"""Material-themed Configurator shell built with PySide6."""
from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, QPoint, QEvent, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
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
    AdminView,
    AppearanceSettingsView,
    BotControlView,
    BotSettingsView,
    DashboardView,
    FavoritesView,
    LlmPromptsView,
    LoraStylesView,
    MainConfigView,
    ToolsView,
)
from material_gui.views.onboarding import FirstRunSetupDialog
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

        self.setWindowTitle("Tenos.ai Configurator")
        self.resize(1320, 860)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinMaxButtonsHint)

        self._drag_active = False
        self._drag_offset = QPoint()

        central = QWidget()
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(0)

        self._surface = QFrame()
        self._surface.setObjectName("MaterialSurface")

        surface_layout = QVBoxLayout(self._surface)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)

        outer_layout.addWidget(self._surface)

        self._build_top_bar(surface_layout)
        self._build_body(surface_layout)

        self.setCentralWidget(central)
        self._apply_material_theme()
        self._set_status("Ready")
        QTimer.singleShot(250, self._maybe_run_auto_update)  # pragma: no cover - startup hook
        QTimer.singleShot(400, self._maybe_show_first_run_tutorial)  # pragma: no cover - startup hook
        QTimer.singleShot(750, self._refresh_runtime_status)  # pragma: no cover - startup hook

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
        title_container.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        logo_label = QLabel()
        logo_label.setObjectName("MaterialAppLogo")
        logo_label.setFixedSize(36, 36)
        logo_path = self._app_base_dir / "tenos-ai_icon.png"
        if not logo_path.exists():
            alt_logo = self._app_base_dir / "tenos-ai_icon.ico"
            if alt_logo.exists():
                logo_path = alt_logo
        pixmap = QPixmap(str(logo_path)) if logo_path.exists() else QPixmap()
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_label.setVisible(False)
        title_row.addWidget(logo_label)

        title = QLabel("Tenos.ai Configurator")
        title.setObjectName("MaterialAppTitle")
        title_row.addWidget(title)
        title_row.addStretch(1)

        subtitle = QLabel("Unified control center for the Tenos.ai bot")
        subtitle.setObjectName("MaterialSubtitle")

        title_container.addLayout(title_row)
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
        nav_container.setMinimumWidth(220)
        nav_container.setMaximumWidth(320)
        nav_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(22, 28, 22, 28)
        nav_layout.setSpacing(18)
        self._nav_container = nav_container
        self._nav_layout = nav_layout

        nav_header = QLabel("Workspace")
        nav_header.setObjectName("NavigationHeading")
        nav_layout.addWidget(nav_header)
        self._nav_header = nav_header

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("MaterialNav")
        self.nav_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.nav_list.setFocusPolicy(Qt.NoFocus)
        self.nav_list.setIconSize(QSize(18, 18))
        self.nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_layout.addWidget(self.nav_list, stretch=1)

        nav_footer = QWidget()
        nav_footer.setObjectName("NavigationFooter")
        footer_layout = QHBoxLayout(nav_footer)
        footer_layout.setContentsMargins(12, 10, 12, 10)
        footer_layout.setSpacing(12)
        self._nav_footer = nav_footer

        self.theme_toggle = QToolButton()
        self.theme_toggle.setObjectName("ThemeToggle")
        self.theme_toggle.setCheckable(True)
        self.theme_toggle.toggled.connect(self._toggle_theme)  # pragma: no cover - Qt binding
        self.theme_toggle.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.theme_toggle.setCursor(Qt.PointingHandCursor)
        footer_layout.addWidget(self.theme_toggle)

        footer_layout.addStretch(1)

        nav_layout.addWidget(nav_footer)

        body.addWidget(nav_container)

        self.stack = AnimatedStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body.addWidget(self.stack, stretch=1)

        parent_layout.addLayout(body)

        # Instantiate views
        self.bot_control_view = BotControlView(
            self._app_base_dir,
            self._repository,
        )
        self.bot_control_view.runtime_state_changed.connect(self._handle_runtime_state_changed)  # pragma: no cover - Qt binding

        self.dashboard_view = DashboardView(
            self._repository,
            app_base_dir=self._app_base_dir,
            on_open_outputs=self._open_outputs,
            status_callback=self._set_status,
            start_callback=self.bot_control_view.start_runtime,
            stop_callback=self.bot_control_view.stop_runtime,
            running_state_provider=self.bot_control_view.is_running,
        )
        self.admin_view = AdminView(self._repository, self._app_base_dir)
        self.main_config_view = MainConfigView(self._repository, self._app_base_dir)
        self.appearance_view = AppearanceSettingsView(
            self._repository,
            on_palette_change=self._handle_theme_palette_update,
            on_mode_change=self._handle_theme_mode_update,
        )
        self.bot_settings_view = BotSettingsView(self._repository)
        self.lora_styles_view = LoraStylesView()
        self.favorites_view = FavoritesView()
        self.llm_prompts_view = LlmPromptsView()
        self.tools_view = ToolsView(self._repository)

        icon_map = {
            "dashboard": QStyle.SP_DesktopIcon,
            "main-config": QStyle.SP_FileIcon,
            "appearance": QStyle.SP_DialogOpenButton,
            "bot-settings": QStyle.SP_DialogApplyButton,
            "lora-styles": QStyle.SP_FileDialogListView,
            "favorites": QStyle.SP_DialogYesButton,
            "llm-prompts": QStyle.SP_FileDialogContentsView,
            "tools": QStyle.SP_DriveHDIcon,
            "admin": QStyle.SP_ComputerIcon,
            "bot-control": QStyle.SP_MediaPlay,
        }

        self._nav_entries = [
            NavigationEntry(
                "Dashboard",
                "dashboard",
                self.dashboard_view,
                lambda: self.dashboard_view.refresh(self._repository),
            ),
            NavigationEntry(
                "Main Config",
                "main-config",
                self.main_config_view,
                lambda: self.main_config_view.refresh(self._repository),
            ),
            NavigationEntry(
                "Appearance",
                "appearance",
                self.appearance_view,
                lambda: self.appearance_view.refresh(self._repository),
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
                "Tools",
                "tools",
                self.tools_view,
                lambda: self.tools_view.refresh(self._repository),
            ),
            NavigationEntry(
                "Admin",
                "admin",
                self.admin_view,
                lambda: self.admin_view.refresh(self._repository),
            ),
            NavigationEntry(
                "Bot Control",
                "bot-control",
                self.bot_control_view,
                lambda: self.bot_control_view.refresh(self._repository),
            ),
        ]

        self._nav_items: list[QListWidgetItem] = []
        self._nav_label_role = Qt.UserRole + 101
        self._compact_nav = False
        self._responsive_breakpoint = 1120

        for entry in self._nav_entries:
            item = QListWidgetItem(entry.title)
            item.setData(Qt.UserRole, entry.slug)
            item.setData(self._nav_label_role, entry.title)
            icon_role = icon_map.get(entry.slug)
            if icon_role is not None:
                item.setIcon(self.style().standardIcon(icon_role))
            self.nav_list.addItem(item)
            self._nav_items.append(item)
            self.stack.addWidget(entry.view)

        self.nav_list.currentRowChanged.connect(self._handle_nav_change)  # pragma: no cover - Qt binding
        self.nav_list.setCurrentRow(0)
        if self.bot_control_view.is_running():
            self._handle_runtime_state_changed(True)

        self._update_maximize_button_icon()
        self._update_responsive_layout()

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

    def _update_responsive_layout(self) -> None:
        if not hasattr(self, "_nav_container"):
            return
        compact = self.width() <= self._responsive_breakpoint
        self._apply_compact_navigation(compact)

    def _apply_compact_navigation(self, compact: bool) -> None:
        if not hasattr(self, "_nav_items"):
            return
        if getattr(self, "_compact_nav", False) == compact:
            return
        self._compact_nav = compact
        if compact:
            self._nav_container.setMaximumWidth(88)
            self._nav_container.setMinimumWidth(88)
            self._nav_layout.setContentsMargins(14, 20, 14, 20)
            if hasattr(self, "_nav_header"):
                self._nav_header.setVisible(False)
            if hasattr(self, "theme_toggle"):
                self.theme_toggle.setToolButtonStyle(Qt.ToolButtonIconOnly)
            for item in self._nav_items:
                label = item.data(self._nav_label_role)
                if isinstance(label, str):
                    item.setText("")
                    item.setToolTip(label)
        else:
            self._nav_container.setMinimumWidth(220)
            self._nav_container.setMaximumWidth(320)
            self._nav_layout.setContentsMargins(22, 28, 22, 28)
            if hasattr(self, "_nav_header"):
                self._nav_header.setVisible(True)
            if hasattr(self, "theme_toggle"):
                self.theme_toggle.setToolButtonStyle(Qt.ToolButtonTextOnly)
            for item in self._nav_items:
                label = item.data(self._nav_label_role)
                if isinstance(label, str):
                    item.setText(label)
                    item.setToolTip(label)

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

    def resizeEvent(self, event):
        self._update_responsive_layout()
        super().resizeEvent(event)

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
            if current_item and current_item.data(Qt.UserRole) == "bot-control":
                self._refresh_runtime_status()
            self._set_status("Configuration refreshed")

        self._run_async(task, on_success, self._handle_task_error)

    def _handle_nav_change(self, index: int) -> None:  # pragma: no cover - Qt binding
        if index >= 0:
            self.stack.setCurrentIndex(index)
            entry = self._nav_entries[index]
            if entry.on_selected is not None:
                entry.on_selected()
            if entry.slug == "bot-control":
                self._refresh_runtime_status()

    def _handle_runtime_state_changed(self, running: bool) -> None:  # pragma: no cover - Qt binding
        if hasattr(self, "dashboard_view") and self.dashboard_view is not None:
            self.dashboard_view.set_runtime_state(running)
        if running:
            self._set_status("Bot running.")
            return
        current_chip = getattr(self, "status_chip", None)
        if current_chip is None:
            self._set_status("Bot idle.")
            return
        label = current_chip.text().strip().lower()
        if label.startswith(("bot running", "launching bot", "bot idle", "ready")):
            self._set_status("Bot idle.")

    def _refresh_runtime_status(self) -> None:
        running = False
        if hasattr(self, "bot_control_view") and self.bot_control_view is not None:
            running = self.bot_control_view.is_running()
        self._handle_runtime_state_changed(running)

    def _handle_update(self) -> None:  # pragma: no cover - Qt binding
        self._begin_update(status_message="Checking for updates…", initiated_by_auto=False)

    def _maybe_show_first_run_tutorial(self) -> None:  # pragma: no cover - UI hook
        if self._repository.has_completed_onboarding():
            return

        dialog = FirstRunSetupDialog(self._repository, self._app_base_dir, parent=self)
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

    def _handle_update_log(self, channel: str, message: str) -> None:
        # Surface important update messages in the status chip while still logging to stdout.
        trimmed = message.strip()
        print(f"[{channel}] {trimmed}")
        if hasattr(self, "bot_control_view") and self.bot_control_view is not None:
            self.bot_control_view.append_system_log(channel, trimmed)
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

    def _handle_theme_mode_update(self, mode: str) -> None:
        next_mode = "light" if mode.strip().lower() == "light" else "dark"
        if next_mode == self._theme_mode:
            self._sync_theme_toggle()
            return
        self._theme_mode = next_mode
        self._apply_material_theme()
        self._persist_theme_preferences()

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
