"""Data access helpers for the Material Configurator UI."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from settings_manager import load_settings, save_settings, get_available_models_for_type

CONFIG_PATH = Path("config.json")
SETTINGS_PATH = Path("settings.json")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


@dataclass(slots=True)
class ConfigSnapshot:
    config: Dict[str, Any]
    settings: Dict[str, Any]


class SettingsRepository:
    """High-level facade for configuration data used in the Material UI."""

    def __init__(self) -> None:
        self._config_cache = _read_json(CONFIG_PATH)
        self._settings_cache = load_settings()

    @property
    def config(self) -> dict[str, Any]:
        return self._config_cache

    @property
    def settings(self) -> dict[str, Any]:
        return self._settings_cache

    def refresh(self) -> ConfigSnapshot:
        self._config_cache = _read_json(CONFIG_PATH)
        self._settings_cache = load_settings()
        return ConfigSnapshot(self._config_cache, self._settings_cache)

    def save_settings(self, updated: dict[str, Any]) -> None:
        merged = dict(self._settings_cache)
        merged.update(updated)
        save_settings(merged)
        self._settings_cache = load_settings()

    def save_config(self, updated: dict[str, Any]) -> None:
        merged = dict(self._config_cache)
        merged.update(updated)
        _write_json(CONFIG_PATH, merged)
        self._config_cache = _read_json(CONFIG_PATH)

    def get_available_models(self, model_type: str) -> list[str]:
        return get_available_models_for_type(model_type)

    # ------------------------------------------------------------------
    # Theme helpers
    # ------------------------------------------------------------------
    def get_theme_preferences(self) -> dict[str, str]:
        settings = self._settings_cache
        return {
            "mode": str(settings.get("theme_mode", "dark")),
            "palette": str(settings.get("theme_palette", "oceanic")),
            "custom_primary": str(settings.get("theme_custom_primary", "#2563EB")),
            "custom_surface": str(settings.get("theme_custom_surface", "#0F172A")),
            "custom_text": str(settings.get("theme_custom_text", "#F1F5F9")),
        }

    def save_theme_preferences(
        self,
        *,
        mode: str,
        palette: str,
        custom_primary: str,
        custom_surface: str,
        custom_text: str,
    ) -> None:
        self.save_settings(
            {
                "theme_mode": mode,
                "theme_palette": palette,
                "theme_custom_primary": custom_primary,
                "theme_custom_surface": custom_surface,
                "theme_custom_text": custom_text,
            }
        )

    # ------------------------------------------------------------------
    # Custom workflow helpers
    # ------------------------------------------------------------------
    def get_custom_workflows(self) -> dict[str, dict[str, Any]]:
        data = self._settings_cache.get("custom_workflows", {})
        if isinstance(data, dict):
            return json.loads(json.dumps(data))
        return {}

    def set_custom_workflow(self, engine: str, slot: str, path: str | None) -> None:
        workflows = self.get_custom_workflows()
        engine_key = engine.lower()
        engine_data = workflows.get(engine_key, {}) if isinstance(workflows.get(engine_key), dict) else {}
        engine_data[slot] = path
        workflows[engine_key] = engine_data
        self.save_settings({"custom_workflows": workflows})


__all__ = ["SettingsRepository", "ConfigSnapshot"]
