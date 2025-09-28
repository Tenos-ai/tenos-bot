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
    from .admin import AdminView  # type: ignore
    from .appearance import AppearanceSettingsView  # type: ignore
    from .dashboard import DashboardView  # type: ignore
    from .main_config import MainConfigView  # type: ignore
    from .bot_settings import BotSettingsView  # type: ignore
    from .lora_styles import LoraStylesView  # type: ignore
    from .favorites import FavoritesView  # type: ignore
    from .llm_prompts import LlmPromptsView  # type: ignore
    from .tools import ToolsView  # type: ignore
    from .bot_control import BotControlView  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - triggered when PySide6 missing
    if exc.name != "PySide6":
        raise
    AdminView = _missing_component("AdminView")  # type: ignore[assignment]
    AppearanceSettingsView = _missing_component("AppearanceSettingsView")  # type: ignore[assignment]
    DashboardView = _missing_component("DashboardView")  # type: ignore[assignment]
    MainConfigView = _missing_component("MainConfigView")  # type: ignore[assignment]
    BotSettingsView = _missing_component("BotSettingsView")  # type: ignore[assignment]
    LoraStylesView = _missing_component("LoraStylesView")  # type: ignore[assignment]
    FavoritesView = _missing_component("FavoritesView")  # type: ignore[assignment]
    LlmPromptsView = _missing_component("LlmPromptsView")  # type: ignore[assignment]
    ToolsView = _missing_component("ToolsView")  # type: ignore[assignment]
    BotControlView = _missing_component("BotControlView")  # type: ignore[assignment]

__all__ = [
    "AdminView",
    "AppearanceSettingsView",
    "DashboardView",
    "MainConfigView",
    "BotSettingsView",
    "LoraStylesView",
    "FavoritesView",
    "LlmPromptsView",
    "ToolsView",
    "BotControlView",
]
