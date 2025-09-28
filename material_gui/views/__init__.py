"""Material view exports with graceful fallbacks when PySide6 is missing."""

from __future__ import annotations

from typing import Any, Callable


def _missing_component(name: str) -> Callable[..., Any]:
    def _raiser(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(
            "Material GUI components require the 'PySide6' package. "
            "Install PySide6 to use the Material configurator."
        )

    _raiser.__name__ = name
    return _raiser


try:  # pragma: no cover - executed only when PySide6 is installed
    from .activity import ActivityLogView  # type: ignore
    from .overview import OverviewView  # type: ignore
    from .discord import DiscordSettingsView  # type: ignore
    from .appearance import AppearanceSettingsView  # type: ignore
    from .custom_workflows import CustomWorkflowSettingsView  # type: ignore
    from .qwen import QwenSettingsView  # type: ignore
    from .system import SystemStatusView  # type: ignore
    from .workflows import WorkflowsView  # type: ignore
    from .admin import NetworkMonitorView  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - triggered when PySide6 missing
    if exc.name != "PySide6":
        raise
    ActivityLogView = _missing_component("ActivityLogView")  # type: ignore[assignment]
    OverviewView = _missing_component("OverviewView")  # type: ignore[assignment]
    DiscordSettingsView = _missing_component("DiscordSettingsView")  # type: ignore[assignment]
    AppearanceSettingsView = _missing_component("AppearanceSettingsView")  # type: ignore[assignment]
    CustomWorkflowSettingsView = _missing_component("CustomWorkflowSettingsView")  # type: ignore[assignment]
    QwenSettingsView = _missing_component("QwenSettingsView")  # type: ignore[assignment]
    SystemStatusView = _missing_component("SystemStatusView")  # type: ignore[assignment]
    WorkflowsView = _missing_component("WorkflowsView")  # type: ignore[assignment]
    NetworkMonitorView = _missing_component("NetworkMonitorView")  # type: ignore[assignment]

__all__ = [
    "ActivityLogView",
    "OverviewView",
    "DiscordSettingsView",
    "AppearanceSettingsView",
    "CustomWorkflowSettingsView",
    "QwenSettingsView",
    "SystemStatusView",
    "WorkflowsView",
    "NetworkMonitorView",
]
