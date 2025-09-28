# --- START OF FILE settings_manager.py ---
# START OF FILE settings_manager.py

import json
import os
import re
import traceback
from types import SimpleNamespace
from typing import TYPE_CHECKING

try:  # pragma: no cover - optional dependency for Discord UI helpers
    import discord  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - allow tests/headless environments
    class _SelectOptionStub:
        __slots__ = ("label", "value", "description", "default", "emoji")

        def __init__(
            self,
            *,
            label: str | None = None,
            value: str | None = None,
            description: str | None = None,
            default: bool = False,
            emoji=None,
        ) -> None:
            self.label = label
            self.value = value
            self.description = description
            self.default = default
            self.emoji = emoji

        def __repr__(self) -> str:  # pragma: no cover - debug helper
            return (
                "SelectOption(label={!r}, value={!r}, description={!r}, default={!r})".format(
                    self.label,
                    self.value,
                    self.description,
                    self.default,
                )
            )

    discord = SimpleNamespace(SelectOption=_SelectOptionStub)

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    import discord  # type: ignore

try:  # pragma: no cover - numpy is optional for headless test runs
    import numpy as np  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback shim
    class _NumpyStub:
        @staticmethod
        def arange(start, stop=None, step=1.0):
            if stop is None:
                stop = float(start)
                start = 0.0
            start = float(start)
            stop = float(stop)
            step = float(step)
            values = []
            current = start
            if step == 0:
                raise ValueError("step must not be zero")
            if step > 0:
                condition = lambda val: val < stop - 1e-9
            else:
                condition = lambda val: val > stop + 1e-9
            while condition(current):
                values.append(current)
                current += step
            return values

    np = _NumpyStub()


def _load_json_if_exists(path: str):
    try:
        if not os.path.exists(path):
            return None
        with open(path, 'r') as file_obj:
            return json.load(file_obj)
    except Exception as exc:  # pragma: no cover - logged upstream
        print(f"SettingsManager: Failed reading {path}: {exc}")
        return None


_HEX_COLOR_PATTERN = re.compile(r"^#?([0-9a-fA-F]{6})$")


def _normalise_hex_color(value: object, fallback: str) -> str:
    """Return a ``#RRGGBB`` string constrained to Material-friendly bounds."""

    if isinstance(value, str):
        candidate = value.strip()
        match = _HEX_COLOR_PATTERN.match(candidate)
        if match:
            return f"#{match.group(1).upper()}"
    return fallback


def _sanitize_custom_workflows(value: object, defaults: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    """Normalise the custom workflow structure while preserving known slots."""

    if not isinstance(value, dict):
        value = {}

    sanitised: dict[str, dict[str, object]] = {}
    for engine, default_slots in defaults.items():
        provided = value.get(engine)
        provided = provided if isinstance(provided, dict) else {}
        engine_slots: dict[str, object] = {}
        for slot_name in default_slots.keys():
            slot_value = provided.get(slot_name)
            if isinstance(slot_value, str):
                slot_value = slot_value.strip() or None
            elif slot_value not in (None, ""):
                slot_value = None
            engine_slots[slot_name] = slot_value
        sanitised[engine] = engine_slots

    # Preserve any additional engines while sanitising their values.
    for engine, provided in value.items():
        if engine in sanitised:
            continue
        if not isinstance(provided, dict):
            continue
        extra_slots: dict[str, object] = {}
        for slot_name, slot_value in provided.items():
            if isinstance(slot_value, str):
                extra_slots[slot_name] = slot_value.strip() or None
            elif slot_value in (None, ""):
                extra_slots[slot_name] = None
        sanitised[engine] = extra_slots

    return sanitised


def get_available_models_for_type(model_type: str) -> list[str]:
    """Return the known model names for the requested workflow type."""

    model_type_normalised = (model_type or "").strip().lower()

    if model_type_normalised == "flux":
        models_data = _load_json_if_exists('modelslist.json') or {}
        favorites = [m.strip() for m in models_data.get('favorites', []) if isinstance(m, str)]
        discovered = []
        for key in ['safetensors', 'sft', 'gguf']:
            values = models_data.get(key, [])
            if isinstance(values, list):
                discovered.extend(v.strip() for v in values if isinstance(v, str))
        merged = favorites + [m for m in discovered if m not in favorites]
        return [m for m in (model.strip() for model in merged) if m]

    if model_type_normalised in {"sdxl", "qwen"}:
        checkpoints_data = _load_json_if_exists('checkpointslist.json') or {}
        favorites = [m.strip() for m in checkpoints_data.get('favorites', []) if isinstance(m, str)]
        discovered: list[str] = []
        if isinstance(checkpoints_data.get('checkpoints'), list):
            discovered.extend(c.strip() for c in checkpoints_data['checkpoints'] if isinstance(c, str))
        else:
            for key, value in checkpoints_data.items():
                if key == 'favorites':
                    continue
                if isinstance(value, list):
                    discovered.extend(v.strip() for v in value if isinstance(v, str))
        merged = [c for c in favorites if c] + [c for c in discovered if c and c not in favorites]

        if model_type_normalised == "qwen":
            qwen_candidates = [c for c in merged if 'qwen' in c.lower()]
            return qwen_candidates or merged

        return merged

    return []


def resolve_model_for_type(settings: dict, model_type: str) -> str | None:
    """Resolve the most appropriate model setting for the provided workflow type."""

    if not isinstance(settings, dict):
        return None

    model_type_normalised = (model_type or "").strip().lower()
    if model_type_normalised not in {"flux", "sdxl", "qwen"}:
        return None

    prefix_map = {
        "flux": "Flux: ",
        "sdxl": "SDXL: ",
        "qwen": "Qwen: ",
    }
    preferred_key_map = {
        "flux": "preferred_model_flux",
        "sdxl": "preferred_model_sdxl",
        "qwen": "preferred_model_qwen",
    }

    prefix = prefix_map[model_type_normalised]
    preferred_key = preferred_key_map[model_type_normalised]

    preferred_value = settings.get(preferred_key)
    if isinstance(preferred_value, str) and preferred_value.strip():
        preferred_value = preferred_value.strip()
        if preferred_value.lower().startswith(prefix.lower()):
            return preferred_value
        return f"{prefix}{preferred_value.split(':', 1)[-1].strip()}"

    selected_model = settings.get('selected_model')
    if isinstance(selected_model, str) and selected_model.strip():
        selected_model = selected_model.strip()
        if selected_model.lower().startswith(prefix.lower()):
            return selected_model

    available_models = get_available_models_for_type(model_type_normalised)
    if available_models:
        return f"{prefix}{available_models[0]}"

    return None

def load_llm_models_config():
    default_config = {
        "providers": {
            "gemini": {"display_name": "Google Gemini API", "models": ["gemini-1.5-flash"]},
            "groq": {"display_name": "Groq API", "models": ["llama3-8b-8192"]},
            "openai": {"display_name": "OpenAI API", "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]}
        }
    }
    try:
        if not os.path.exists('llm_models.json'):
            print("SettingsManager: llm_models.json not found. Using default.")
            return default_config # Return immediately after creating/using default
        with open('llm_models.json', 'r') as f:
            config = json.load(f)
        if not isinstance(config, dict) or "providers" not in config or not isinstance(config["providers"], dict):
            print("SettingsManager Error: llm_models.json has invalid structure. Using default.")
            return default_config
        # Ensure OpenAI provider exists, add if not (for backward compatibility)
        if "openai" not in config["providers"]:
            print("SettingsManager: Adding default OpenAI provider to llm_models.json")
            if "providers" not in config: config["providers"] = {}
            config["providers"]["openai"] = default_config["providers"]["openai"]
            # Optionally save back the updated config
            # try:
            #     with open('llm_models.json', 'w') as f_write:
            #         json.dump(config, f_write, indent=2)
            # except Exception as e_write:
            #     print(f"SettingsManager Error: Could not save updated llm_models.json: {e_write}")

        for key, data in config["providers"].items():
            if not isinstance(data, dict) or "display_name" not in data or "models" not in data or not isinstance(data["models"], list):
                print(f"SettingsManager Warning: Invalid structure for provider '{key}'. Reverting to default for this provider.")
                # Use .get for safer access to default_config in case a new provider was added manually but is malformed
                config["providers"][key] = default_config["providers"].get(key, {"display_name": key, "models": []})
        return config
    except (OSError, json.JSONDecodeError) as e:
        print(f"SettingsManager Error loading llm_models.json: {e}. Using default.")
        return default_config
    except Exception as e:
        print(f"SettingsManager Unexpected error loading llm_models.json: {e}")
        traceback.print_exc()
        return default_config

llm_models_config = load_llm_models_config()


def load_styles_config():
    try:
        if not os.path.exists('styles_config.json'):
            print("Warning: styles_config.json not found.")
            return {"off": {"favorite": False}}
        with open('styles_config.json', 'r') as f:
            styles = json.load(f)
        if not isinstance(styles, dict):
            print("Error: styles_config.json is not a valid dictionary.")
            return {"off": {"favorite": False}}
        if 'off' not in styles: styles['off'] = {"favorite": False}
        keys_to_remove = []
        for k, v in styles.items():
            if not isinstance(v, dict):
                print(f"Warning: Style '{k}' value is not a dict in styles_config.json. Resetting/Removing.")
                keys_to_remove.append(k)
        for k in keys_to_remove:
            del styles[k]
        if 'off' not in styles: styles['off'] = {"favorite": False}
        return styles
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error loading styles_config.json: {e}. Returning default.")
        return {"off": {"favorite": False}}
    except Exception as e:
        print(f"Unexpected error loading styles_config.json: {e}")
        traceback.print_exc()
        return {"off": {"favorite": False}}


def load_settings():
    settings_file = 'settings.json'
    try:
        if not os.path.exists(settings_file):
            print(f"Warning: {settings_file} not found. Creating default settings.")
            settings = _get_default_settings()
            save_settings(settings)
            return settings

        with open(settings_file, 'r') as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error parsing {settings_file} (invalid JSON): {e}. Returning defaults.")
                return _get_default_settings()
        
        # --- Migration for old 'default_style' key ---
        if 'default_style' in settings:
            old_style_value = settings.pop('default_style')
            if 'default_style_flux' not in settings:
                settings['default_style_flux'] = old_style_value
            if 'default_style_sdxl' not in settings:
                settings['default_style_sdxl'] = old_style_value
            print("Migrated 'default_style' to 'default_style_flux' and 'default_style_sdxl'.")


        default_settings = _get_default_settings()
        updated = False
        for key, default_value in default_settings.items():
            if key not in settings:
                print(f"Warning: Setting '{key}' missing. Adding default value: {default_value}")
                settings[key] = default_value
                updated = True

        numeric_keys_float = ['default_guidance', 'default_guidance_sdxl', 'upscale_factor', 'default_mp_size', 'kontext_guidance', 'kontext_mp_size']
        numeric_keys_int = ['steps', 'sdxl_steps', 'default_batch_size', 'kontext_steps', 'variation_batch_size']
        bool_keys = ['remix_mode', 'llm_enhancer_enabled']
        display_prompt_key = 'display_prompt_preference'
        allowed_display_prompt_options = ['enhanced', 'original']


        for key in numeric_keys_float:
             if key in settings:
                 try:
                     if settings[key] is None: continue
                     settings[key] = float(settings[key])
                 except (ValueError, TypeError):
                      print(f"Warning: Setting '{key}' has invalid type ({type(settings[key])}). Resetting to default.")
                      settings[key] = default_settings[key]
                      updated = True

        for key in numeric_keys_int:
            if key in settings:
                 try:
                     if settings[key] is None: continue
                     settings[key] = int(settings[key])
                 except (ValueError, TypeError):
                      print(f"Warning: Setting '{key}' has invalid type ({type(settings[key])}). Resetting to default.")
                      settings[key] = default_settings[key]
                      updated = True

        for key in bool_keys:
            if key in settings:
                if isinstance(settings[key], bool): continue
                elif isinstance(settings[key], str):
                    new_val = settings[key].lower() in ['true', '1', 't', 'y', 'yes', 'on']
                    if new_val != settings[key]: updated = True
                    settings[key] = new_val
                elif isinstance(settings[key], (int, float)):
                     new_val = bool(settings[key])
                     if new_val != settings[key]: updated = True
                     settings[key] = new_val
                else:
                    print(f"Warning: Setting '{key}' has invalid type ({type(settings[key])}). Resetting to default.")
                    settings[key] = default_settings[key]
                    updated = True

        if display_prompt_key in settings:
            current_display_pref = str(settings[display_prompt_key]).lower()
            if current_display_pref not in allowed_display_prompt_options:
                print(f"Warning: Setting '{display_prompt_key}' has invalid value '{current_display_pref}'. Resetting to default.")
                settings[display_prompt_key] = default_settings[display_prompt_key]
                updated = True
            else:
                settings[display_prompt_key] = current_display_pref
        else: # Should be added by loop above if missing
             pass


        llm_string_keys = ['llm_provider', 'llm_model_gemini', 'llm_model_groq', 'llm_model_openai']
        for key in llm_string_keys:
            if key in settings:
                if settings[key] is None or isinstance(settings[key], str):
                    if isinstance(settings[key], str):
                        stripped_val = settings[key].strip()
                        if settings[key] != stripped_val: updated = True # If stripping changed it
                        settings[key] = stripped_val
                    continue
                else:
                    print(f"Warning: Setting '{key}' has invalid type ({type(settings[key])}). Resetting to default.")
                    settings[key] = default_settings[key]
                    updated = True

        allowed_providers = list(llm_models_config.get('providers', {}).keys())
        if not allowed_providers: allowed_providers = ['gemini'] # Fallback
        if settings.get('llm_provider') not in allowed_providers:
            print(f"Warning: Invalid 'llm_provider' value '{settings.get('llm_provider')}'. Resetting to default '{default_settings['llm_provider']}'.")
            settings['llm_provider'] = default_settings['llm_provider']
            updated = True

        # --- Theme normalisation ---
        theme_mode = str(settings.get('theme_mode', default_settings['theme_mode'])).strip().lower()
        if theme_mode not in {'dark', 'light'}:
            theme_mode = default_settings['theme_mode']
            updated = True
        settings['theme_mode'] = theme_mode

        theme_palette = settings.get('theme_palette', default_settings['theme_palette'])
        if isinstance(theme_palette, str):
            theme_palette = theme_palette.strip().lower() or default_settings['theme_palette']
        else:
            theme_palette = default_settings['theme_palette']
            updated = True
        settings['theme_palette'] = theme_palette

        for color_key in ('theme_custom_primary', 'theme_custom_surface', 'theme_custom_text'):
            current_value = settings.get(color_key, default_settings[color_key])
            normalised = _normalise_hex_color(current_value, default_settings[color_key])
            if normalised != current_value:
                updated = True
            settings[color_key] = normalised

        # --- Discord profile metadata ---
        for discord_key in ('discord_display_name', 'discord_avatar_path'):
            value = settings.get(discord_key, "")
            if isinstance(value, str):
                stripped = value.strip()
                if stripped != value:
                    updated = True
                settings[discord_key] = stripped
            else:
                settings[discord_key] = ""
                updated = True

        # --- Custom workflow overrides ---
        settings['custom_workflows'] = _sanitize_custom_workflows(
            settings.get('custom_workflows'),
            default_settings['custom_workflows'],
        )

        # --- Model and CLIP Validation with Normalization ---
        available_flux_models_raw = []
        try:
            if os.path.exists('modelslist.json'):
                 with open('modelslist.json', 'r') as f: models_list_data = json.load(f)
                 if isinstance(models_list_data, dict):
                     for type_list in models_list_data.values():
                         if isinstance(type_list, list): available_flux_models_raw.extend([m for m in type_list if isinstance(m, str)])
                     available_flux_models_raw = list(set(available_flux_models_raw))
        except Exception as e: print(f"Warning: Could not load modelslist.json for Flux model validation: {e}")
        # Create a map of lowercase stripped name -> original stripped name for case-insensitive matching while preserving original casing
        available_flux_models = {m.strip().lower(): m.strip() for m in available_flux_models_raw}

        available_sdxl_checkpoints_raw = []
        try:
            if os.path.exists('checkpointslist.json'):
                 with open('checkpointslist.json', 'r') as f: checkpoints_list_data = json.load(f)
                 if isinstance(checkpoints_list_data, dict):
                     if isinstance(checkpoints_list_data.get('checkpoints'), list):
                         available_sdxl_checkpoints_raw.extend([c for c in checkpoints_list_data['checkpoints'] if isinstance(c, str)])
                     else: # Fallback for other structures if 'checkpoints' key is not a list
                        for key_chk, value_chk in checkpoints_list_data.items():
                            if isinstance(value_chk, list) and key_chk != 'favorites':
                                available_sdxl_checkpoints_raw.extend([c for c in value_chk if isinstance(c, str)])
                     available_sdxl_checkpoints_raw = list(set(available_sdxl_checkpoints_raw))
        except Exception as e: print(f"Warning: Could not load checkpointslist.json for SDXL model validation: {e}")
        available_sdxl_checkpoints = {c.strip().lower(): c.strip() for c in available_sdxl_checkpoints_raw}


        current_selected_model_setting = settings.get('selected_model')
        if current_selected_model_setting and isinstance(current_selected_model_setting, str):
            current_selected_model_setting_stripped = current_selected_model_setting.strip()
            model_type, model_name_from_setting = None, current_selected_model_setting_stripped
            if ":" in current_selected_model_setting_stripped:
                 model_type, model_name_from_setting = current_selected_model_setting_stripped.split(":", 1)
                 model_type = model_type.strip().lower(); model_name_from_setting = model_name_from_setting.strip() # Already stripped above, but good practice

            valid_current_model_found = False
            if model_type == "flux":
                if model_name_from_setting.lower() in available_flux_models:
                    # Ensure the stored value matches the original casing from the list
                    correctly_cased_name = available_flux_models[model_name_from_setting.lower()]
                    new_setting_val = f"Flux: {correctly_cased_name}"
                    if settings['selected_model'] != new_setting_val: updated = True
                    settings['selected_model'] = new_setting_val
                    valid_current_model_found = True
            elif model_type == "sdxl":
                if model_name_from_setting.lower() in available_sdxl_checkpoints:
                    correctly_cased_name = available_sdxl_checkpoints[model_name_from_setting.lower()]
                    new_setting_val = f"SDXL: {correctly_cased_name}"
                    if settings['selected_model'] != new_setting_val: updated = True
                    settings['selected_model'] = new_setting_val
                    valid_current_model_found = True
            elif model_type is None : # Old format (no prefix), try to match and fix
                if model_name_from_setting.lower() in available_flux_models:
                    settings['selected_model'] = f"Flux: {available_flux_models[model_name_from_setting.lower()]}"
                    valid_current_model_found = True; updated = True
                elif model_name_from_setting.lower() in available_sdxl_checkpoints:
                    settings['selected_model'] = f"SDXL: {available_sdxl_checkpoints[model_name_from_setting.lower()]}"
                    valid_current_model_found = True; updated = True

            if not valid_current_model_found:
                print(f"⚠️ Warning: Selected model '{current_selected_model_setting}' not found or type mismatch. Resetting.")
                if available_flux_models:
                    first_flux_model = next(iter(available_flux_models.values()))
                    settings['selected_model'] = f"Flux: {first_flux_model}"
                elif available_sdxl_checkpoints:
                    first_sdxl_model = next(iter(available_sdxl_checkpoints.values()))
                    settings['selected_model'] = f"SDXL: {first_sdxl_model}"
                else:
                    settings['selected_model'] = None
                updated = True
            elif current_selected_model_setting != settings['selected_model']: # If stripping or casing correction happened
                updated = True

        elif not current_selected_model_setting and (available_flux_models or available_sdxl_checkpoints): # If None but models exist
            if available_flux_models: settings['selected_model'] = f"Flux: {next(iter(available_flux_models.values()))}"
            elif available_sdxl_checkpoints: settings['selected_model'] = f"SDXL: {next(iter(available_sdxl_checkpoints.values()))}"
            updated = True
            
        current_kontext_model = settings.get('selected_kontext_model')
        if current_kontext_model and isinstance(current_kontext_model, str):
            current_kontext_model_norm = current_kontext_model.strip()
            if current_kontext_model_norm.lower() not in available_flux_models:
                print(f"⚠️ Warning: Selected Kontext Model '{current_kontext_model}' not found in Flux models list. Resetting.")
                settings['selected_kontext_model'] = next(iter(available_flux_models.values())) if available_flux_models else None
                updated = True
            elif current_kontext_model != available_flux_models.get(current_kontext_model_norm.lower()):
                settings['selected_kontext_model'] = available_flux_models.get(current_kontext_model_norm.lower())
                updated = True
        elif not current_kontext_model and available_flux_models: # If no kontext model is set, but flux models exist
            settings['selected_kontext_model'] = next(iter(available_flux_models.values())) # Default to the first flux model
            updated = True


        available_clips_t5_raw = []; available_clips_l_raw = []
        try:
            if os.path.exists('cliplist.json'):
                with open('cliplist.json', 'r') as f: clips_list_data = json.load(f)
                if isinstance(clips_list_data, dict):
                    available_clips_t5_raw = [c for c in clips_list_data.get('t5', []) if isinstance(c, str)]
                    available_clips_l_raw = [c for c in clips_list_data.get('clip_L', []) if isinstance(c, str)]
        except Exception as e: print(f"Warning: Could not load cliplist.json for validation: {e}")

        available_clips_t5 = {c.strip().lower(): c.strip() for c in available_clips_t5_raw}
        available_clips_l = {c.strip().lower(): c.strip() for c in available_clips_l_raw}

        current_t5_clip = settings.get('selected_t5_clip')
        if current_t5_clip and isinstance(current_t5_clip, str):
            current_t5_clip_norm = current_t5_clip.strip()
            if current_t5_clip_norm.lower() not in available_clips_t5:
                print(f"⚠️ Warning: Selected T5 CLIP '{current_t5_clip}' not found. Resetting.")
                settings['selected_t5_clip'] = next(iter(available_clips_t5.values())) if available_clips_t5 else None
                updated = True
            elif current_t5_clip != available_clips_t5.get(current_t5_clip_norm.lower()): # Correct casing/spacing
                settings['selected_t5_clip'] = available_clips_t5.get(current_t5_clip_norm.lower())
                updated = True
        elif not current_t5_clip and available_clips_t5:
            settings['selected_t5_clip'] = next(iter(available_clips_t5.values()))
            updated = True


        current_clip_l = settings.get('selected_clip_l')
        if current_clip_l and isinstance(current_clip_l, str):
            current_clip_l_norm = current_clip_l.strip()
            if current_clip_l_norm.lower() not in available_clips_l:
                 print(f"⚠️ Warning: Selected CLIP-L '{current_clip_l}' not found. Resetting.")
                 settings['selected_clip_l'] = next(iter(available_clips_l.values())) if available_clips_l else None
                 updated = True
            elif current_clip_l != available_clips_l.get(current_clip_l_norm.lower()):
                settings['selected_clip_l'] = available_clips_l.get(current_clip_l_norm.lower())
                updated = True
        elif not current_clip_l and available_clips_l:
            settings['selected_clip_l'] = next(iter(available_clips_l.values()))
            updated = True


        selected_provider = settings.get('llm_provider', 'gemini') # Already stripped

        def validate_llm_model(provider_short_name):
            nonlocal updated
            model_key = f"llm_model_{provider_short_name}"
            current_llm_model_setting = settings.get(model_key)
            current_llm_model = current_llm_model_setting.strip() if isinstance(current_llm_model_setting, str) else None

            specific_provider_models_raw = llm_models_config.get('providers', {}).get(provider_short_name, {}).get('models', [])
            specific_provider_models_map = {m.strip().lower(): m.strip() for m in specific_provider_models_raw}


            if current_llm_model: # If a model is set for this provider type
                if current_llm_model.lower() not in specific_provider_models_map:
                    print(f"⚠️ Warning: Selected {provider_short_name.capitalize()} model '{current_llm_model_setting}' invalid for this provider. Resetting.")
                    settings[model_key] = next(iter(specific_provider_models_map.values())) if specific_provider_models_map else default_settings[model_key]
                    updated = True
                elif current_llm_model_setting != specific_provider_models_map.get(current_llm_model.lower()): # Correct casing/spacing
                    settings[model_key] = specific_provider_models_map.get(current_llm_model.lower())
                    updated = True
            elif not current_llm_model and specific_provider_models_map: # If None but models exist for this provider type
                settings[model_key] = next(iter(specific_provider_models_map.values()))
                updated = True

        validate_llm_model('gemini')
        validate_llm_model('groq')
        validate_llm_model('openai')

        if 'default_sdxl_negative_prompt' in settings and isinstance(settings['default_sdxl_negative_prompt'], str):
            settings['default_sdxl_negative_prompt'] = settings['default_sdxl_negative_prompt'].strip()
        elif 'default_sdxl_negative_prompt' not in settings:  # Ensure key exists
            settings['default_sdxl_negative_prompt'] = default_settings['default_sdxl_negative_prompt']
            updated = True

        if 'default_qwen_negative_prompt' in settings and isinstance(settings['default_qwen_negative_prompt'], str):
            settings['default_qwen_negative_prompt'] = settings['default_qwen_negative_prompt'].strip()
        elif 'default_qwen_negative_prompt' not in settings:
            settings['default_qwen_negative_prompt'] = default_settings['default_qwen_negative_prompt']
            updated = True


        preferred_flux = settings.get('preferred_model_flux')
        if preferred_flux is not None and not isinstance(preferred_flux, str):
            settings['preferred_model_flux'] = None
            updated = True

        preferred_sdxl = settings.get('preferred_model_sdxl')
        if preferred_sdxl is not None and not isinstance(preferred_sdxl, str):
            settings['preferred_model_sdxl'] = None
            updated = True

        preferred_qwen = settings.get('preferred_model_qwen')
        if preferred_qwen is not None and not isinstance(preferred_qwen, str):
            settings['preferred_model_qwen'] = None
            updated = True

        selected_model_setting = settings.get('selected_model')
        if isinstance(selected_model_setting, str):
            selected_model_setting = selected_model_setting.strip()

        if not settings.get('preferred_model_flux') and selected_model_setting and selected_model_setting.lower().startswith('flux:'):
            settings['preferred_model_flux'] = selected_model_setting
            updated = True

        if not settings.get('preferred_model_sdxl') and selected_model_setting and selected_model_setting.lower().startswith('sdxl:'):
            settings['preferred_model_sdxl'] = selected_model_setting
            updated = True

        if not settings.get('preferred_model_qwen') and selected_model_setting and selected_model_setting.lower().startswith('qwen:'):
            settings['preferred_model_qwen'] = selected_model_setting
            updated = True

        if updated:
             print(f"Updating {settings_file} with defaults/corrections.")
             save_settings(settings)

        return settings
    except OSError as e:
        print(f"Error reading {settings_file}: {e}. Returning defaults.")
        return _get_default_settings()
    except Exception as e:
        print(f"Unexpected error loading settings: {e}")
        traceback.print_exc()
        return _get_default_settings()

def _get_default_settings():
    default_flux_model_raw = None
    try:
        if os.path.exists('modelslist.json'):
            with open('modelslist.json', 'r') as f: models = json.load(f)
            default_flux_model_raw = next((m.strip() for type_list in models.values() if isinstance(type_list, list) for m in type_list if isinstance(m, str) and m.strip()), None)
    except Exception: default_flux_model_raw = None

    default_sdxl_checkpoint_raw = None
    default_qwen_checkpoint_raw = None
    try:
        if os.path.exists('checkpointslist.json'):
            with open('checkpointslist.json', 'r') as f:
                checkpoints = json.load(f)
            if isinstance(checkpoints, dict):
                candidate_lists = []
                if isinstance(checkpoints.get('checkpoints'), list):
                    candidate_lists.append(checkpoints['checkpoints'])
                for key, value in checkpoints.items():
                    if key == 'favorites':
                        continue
                    if isinstance(value, list):
                        candidate_lists.append(value)
            elif isinstance(checkpoints, list):
                candidate_lists = [checkpoints]
            else:
                candidate_lists = []

            for lst in candidate_lists:
                for entry in lst:
                    if not isinstance(entry, str):
                        continue
                    cleaned = entry.strip()
                    if not cleaned:
                        continue
                    if default_qwen_checkpoint_raw is None and 'qwen' in cleaned.lower():
                        default_qwen_checkpoint_raw = cleaned
                    if default_sdxl_checkpoint_raw is None and 'qwen' not in cleaned.lower():
                        default_sdxl_checkpoint_raw = cleaned
                    if default_sdxl_checkpoint_raw and default_qwen_checkpoint_raw:
                        break
                if default_sdxl_checkpoint_raw and default_qwen_checkpoint_raw:
                    break
    except Exception:
        default_sdxl_checkpoint_raw = None
        default_qwen_checkpoint_raw = default_qwen_checkpoint_raw or None

    default_model_setting = None
    if default_flux_model_raw:
        default_model_setting = f"Flux: {default_flux_model_raw}"
    elif default_sdxl_checkpoint_raw:
        default_model_setting = f"SDXL: {default_sdxl_checkpoint_raw}"
    elif default_qwen_checkpoint_raw:
        default_model_setting = f"Qwen: {default_qwen_checkpoint_raw}"

    preferred_flux_default = (
        default_model_setting
        if default_model_setting and default_model_setting.lower().startswith('flux:')
        else (f"Flux: {default_flux_model_raw}" if default_flux_model_raw else None)
    )
    preferred_sdxl_default = (
        default_model_setting
        if default_model_setting and default_model_setting.lower().startswith('sdxl:')
        else (f"SDXL: {default_sdxl_checkpoint_raw}" if default_sdxl_checkpoint_raw else None)
    )
    preferred_qwen_default = (
        default_model_setting
        if default_model_setting and default_model_setting.lower().startswith('qwen:')
        else (f"Qwen: {default_qwen_checkpoint_raw}" if default_qwen_checkpoint_raw else None)
    )

    default_t5 = None; default_l = None
    try:
        if os.path.exists('cliplist.json'):
            with open('cliplist.json', 'r') as f: clips = json.load(f)
            t5_list = clips.get('t5', []); l_list = clips.get('clip_L', [])
            default_t5 = next((c.strip() for c in t5_list if isinstance(c, str) and c.strip()), None) if isinstance(t5_list, list) else None
            default_l = next((c.strip() for c in l_list if isinstance(c, str) and c.strip()), None) if isinstance(l_list, list) else None
    except Exception: default_t5 = None; default_l = None

    default_gemini_model_raw = llm_models_config.get('providers', {}).get('gemini', {}).get('models', ["gemini-1.5-flash"])[0]
    default_groq_model_raw = llm_models_config.get('providers', {}).get('groq', {}).get('models', ["llama3-8b-8192"])[0]
    default_openai_model_raw = llm_models_config.get('providers', {}).get('openai', {}).get('models', ["gpt-3.5-turbo"])[0]
    return {
        "selected_model": default_model_setting,
        "preferred_model_flux": preferred_flux_default,
        "preferred_model_sdxl": preferred_sdxl_default,
        "preferred_model_qwen": preferred_qwen_default,
        "selected_kontext_model": default_flux_model_raw,
        "steps": 32,
        "sdxl_steps": 26,
        "selected_t5_clip": default_t5,
        "selected_clip_l": default_l,
        "selected_upscale_model": None,
        "selected_vae": None,
        "default_style_flux": "off",
        "default_style_sdxl": "off",
        "default_style_qwen": "off",
        "default_variation_mode": "weak",
        "variation_batch_size": 1,
        "default_batch_size": 1,
        "default_guidance": 3.5,
        "default_guidance_sdxl": 7.0,
        "default_sdxl_negative_prompt": "",
        "default_qwen_negative_prompt": "",
        "default_mp_size": 1.0,
        "kontext_guidance": 3.0,
        "kontext_steps": 32,
        "kontext_mp_size": 1.15,
        "default_edit_engine": "kontext",
        "qwen_edit_steps": 30,
        "qwen_edit_guidance": 6.0,
        "qwen_edit_denoise": 0.65,
        "remix_mode": False,
        "upscale_factor": 1.85,
        "llm_enhancer_enabled": False,
        "llm_provider": "gemini",
        "llm_model_gemini": default_gemini_model_raw.strip() if default_gemini_model_raw else "gemini-1.5-flash",
        "llm_model_groq": default_groq_model_raw.strip() if default_groq_model_raw else "llama3-8b-8192",
        "llm_model_openai": default_openai_model_raw.strip() if default_openai_model_raw else "gpt-3.5-turbo",
        "display_prompt_preference": "enhanced",
        "theme_mode": "dark",
        "theme_palette": "oceanic",
        "theme_custom_primary": "#2563EB",
        "theme_custom_surface": "#0F172A",
        "theme_custom_text": "#F1F5F9",
        "discord_display_name": "",
        "discord_avatar_path": "",
        "custom_workflows": {
            "flux": {
                "text_to_image": None,
                "img2img": None,
                "variation_weak": None,
                "variation_strong": None,
                "upscale": None,
            },
            "sdxl": {
                "text_to_image": None,
                "img2img": None,
                "variation": None,
                "upscale": None,
            },
            "qwen": {
                "text_to_image": None,
                "img2img": None,
                "variation": None,
                "upscale": None,
                "edit": None,
            },
        },
    }

def save_settings(settings):
    settings_file = 'settings.json'
    try:
        numeric_keys_float = ['default_guidance', 'default_guidance_sdxl', 'upscale_factor', 'default_mp_size', 'kontext_guidance', 'kontext_mp_size', 'qwen_edit_guidance', 'qwen_edit_denoise']
        numeric_keys_int = ['steps', 'sdxl_steps', 'default_batch_size', 'kontext_steps', 'variation_batch_size', 'qwen_edit_steps']
        bool_keys = ['remix_mode', 'llm_enhancer_enabled']
        string_keys_to_strip = [
            'llm_provider', 'llm_model_gemini', 'llm_model_groq', 'llm_model_openai',
            'selected_model', 'selected_t5_clip', 'selected_clip_l', 'selected_upscale_model',
            'selected_vae', 'default_style_flux', 'default_style_sdxl', 'default_style_qwen',
            'default_sdxl_negative_prompt', 'default_qwen_negative_prompt',
            'selected_kontext_model', 'preferred_model_flux', 'preferred_model_sdxl', 'preferred_model_qwen',
            'default_edit_engine', 'discord_display_name', 'discord_avatar_path',
            'theme_mode', 'theme_palette', 'theme_custom_primary', 'theme_custom_surface', 'theme_custom_text'
        ]
        display_prompt_key = 'display_prompt_preference'
        allowed_display_prompt_options = ['enhanced', 'original']


        valid_settings = settings.copy()
        defaults = _get_default_settings()

        for key in numeric_keys_float:
             if key in valid_settings:
                 try:
                     if valid_settings[key] is None: continue
                     valid_settings[key] = float(valid_settings[key])
                 except (ValueError, TypeError): valid_settings[key] = defaults[key]

        for key in numeric_keys_int:
             if key in valid_settings:
                 try:
                     if valid_settings[key] is None: continue
                     valid_settings[key] = int(valid_settings[key])
                 except (ValueError, TypeError): valid_settings[key] = defaults[key]

        for key in bool_keys:
             if key in valid_settings:
                 if isinstance(valid_settings[key], str): valid_settings[key] = valid_settings[key].lower() in ['true', '1', 't', 'y', 'yes', 'on']
                 else: valid_settings[key] = bool(valid_settings[key])

        for key in string_keys_to_strip:
            if key in valid_settings and isinstance(valid_settings[key], str):
                valid_settings[key] = valid_settings[key].strip()
            elif key in valid_settings and valid_settings[key] is None and key not in ['selected_model', 'selected_t5_clip', 'selected_clip_l', 'selected_upscale_model', 'selected_vae', 'selected_kontext_model', 'preferred_model_flux', 'preferred_model_sdxl', 'preferred_model_qwen']: # Allow None for model selections
                if defaults[key] is not None: 
                    print(f"Warning: '{key}' is None but expects a string. Resetting to default.")
                    valid_settings[key] = defaults[key]


        allowed_providers = list(llm_models_config.get('providers', {}).keys())
        if not allowed_providers: allowed_providers = ['gemini']
        if valid_settings.get('llm_provider') not in allowed_providers:
            valid_settings['llm_provider'] = defaults['llm_provider']

        if display_prompt_key in valid_settings:
            display_pref_val = str(valid_settings[display_prompt_key]).lower()
            if display_pref_val not in allowed_display_prompt_options: valid_settings[display_prompt_key] = defaults[display_prompt_key]
            else: valid_settings[display_prompt_key] = display_pref_val

        theme_mode = valid_settings.get('theme_mode', defaults['theme_mode'])
        if isinstance(theme_mode, str):
            theme_mode = theme_mode.strip().lower()
            if theme_mode not in {'dark', 'light'}:
                theme_mode = defaults['theme_mode']
        else:
            theme_mode = defaults['theme_mode']
        valid_settings['theme_mode'] = theme_mode

        theme_palette = valid_settings.get('theme_palette', defaults['theme_palette'])
        if isinstance(theme_palette, str):
            theme_palette = theme_palette.strip().lower() or defaults['theme_palette']
        else:
            theme_palette = defaults['theme_palette']
        valid_settings['theme_palette'] = theme_palette

        for color_key in ('theme_custom_primary', 'theme_custom_surface', 'theme_custom_text'):
            current_value = valid_settings.get(color_key, defaults[color_key])
            valid_settings[color_key] = _normalise_hex_color(current_value, defaults[color_key])

        if 'custom_workflows' in valid_settings:
            valid_settings['custom_workflows'] = _sanitize_custom_workflows(
                valid_settings['custom_workflows'],
                defaults['custom_workflows'],
            )

        for key in defaults:
            if key not in valid_settings:
                print(f"Warning: Key '{key}' missing before saving. Adding default.")
                valid_settings[key] = defaults[key]

        with open(settings_file, 'w') as f:
            json.dump(valid_settings, f, indent=2)
    except OSError as e: print(f"Error writing {settings_file}: {e}")
    except TypeError as e: print(f"Type error while saving settings: {e}")
    except Exception as e: print(f"Unexpected error saving settings: {e}"); traceback.print_exc()


def get_model_choices(settings):
    choices: list[discord.SelectOption] = []

    def _load_json_dict(path: str) -> dict:
        try:
            if os.path.exists(path):
                with open(path, 'r') as fp:
                    data = json.load(fp)
                    return data if isinstance(data, dict) else {}
        except Exception:
            pass
        return {}

    flux_models_data = _load_json_dict('modelslist.json')
    checkpoints_data = _load_json_dict('checkpointslist.json')

    current_model_setting = settings.get('selected_model')
    if isinstance(current_model_setting, str):
        current_model_setting = current_model_setting.strip()

    def _clean_list(values):
        cleaned: list[str] = []
        for value in values or []:
            if isinstance(value, str):
                normalised = value.strip()
                if normalised:
                    cleaned.append(normalised)
        return cleaned

    def _split_qwen(values: list[str]) -> tuple[list[str], list[str]]:
        qwen_items: list[str] = []
        other_items: list[str] = []
        for item in values:
            (qwen_items if 'qwen' in item.lower() else other_items).append(item)
        return qwen_items, other_items

    flux_favorites = _clean_list(flux_models_data.get('favorites', []))
    flux_pool: list[str] = []
    for key in ('safetensors', 'sft', 'gguf'):
        flux_pool.extend(_clean_list(flux_models_data.get(key, [])))

    checkpoint_lists: list[str] = []
    if isinstance(checkpoints_data.get('checkpoints'), list):
        checkpoint_lists.extend(_clean_list(checkpoints_data.get('checkpoints')))
    else:
        for key, value in checkpoints_data.items():
            if key == 'favorites':
                continue
            checkpoint_lists.extend(_clean_list(value))

    sdxl_favorites_all = _clean_list(checkpoints_data.get('favorites', []))
    qwen_favorites, sdxl_favorites = _split_qwen(sdxl_favorites_all)
    qwen_all, sdxl_all = _split_qwen(checkpoint_lists)

    catalogue = [
        (
            'flux',
            '[FLUX]',
            flux_favorites,
            flux_pool,
        ),
        (
            'sdxl',
            '[SDXL]',
            sdxl_favorites,
            sdxl_all,
        ),
        (
            'qwen',
            '[QWEN]',
            qwen_favorites,
            qwen_all,
        ),
    ]

    canonical_options: list[dict[str, str]] = []
    seen_values: set[str] = set()

    for model_type, label_prefix, favorites, pool in catalogue:
        prefix = f"{model_type.capitalize()}: "
        for model_name in sorted(set(favorites)):
            value = f"{prefix}{model_name}"
            if value in seen_values:
                continue
            canonical_options.append({'label': f"⭐ {label_prefix} {model_name}", 'value': value})
            seen_values.add(value)

        for model_name in sorted(set(pool)):
            value = f"{prefix}{model_name}"
            if value in seen_values:
                continue
            canonical_options.append({'label': f"{label_prefix} {model_name}", 'value': value})
            seen_values.add(value)

    if current_model_setting and current_model_setting not in seen_values:
        if ':' in current_model_setting:
            type_prefix, actual_name = current_model_setting.split(':', 1)
            type_prefix = type_prefix.strip().upper()
            actual_name = actual_name.strip()
        else:
            type_prefix = 'MODEL'
            actual_name = current_model_setting
        label = f"[{type_prefix}] {actual_name}"
        canonical_options.insert(0, {'label': label, 'value': current_model_setting})

    for option in canonical_options:
        is_default = option['value'] == current_model_setting
        choices.append(
            discord.SelectOption(
                label=option['label'][:100],
                value=option['value'],
                default=is_default,
            )
        )

    if choices and not any(opt.default for opt in choices):
        choices[0].default = True

    return choices[:25]


def get_clip_choices(settings, clip_type_key, setting_key):
    choices = []
    clips_data = {}
    try:
        if os.path.exists('cliplist.json'):
            with open('cliplist.json', 'r') as f:
                clips_data = json.load(f)
        if not isinstance(clips_data, dict):
            clips_data = {}
    except Exception as e:
        print(f"Error loading cliplist.json: {e}")
        clips_data = {}

    current_clip = settings.get(setting_key)
    if isinstance(current_clip, str):
        current_clip = current_clip.strip()

    favorites_raw = clips_data.get('favorites', {}).get(clip_type_key, [])
    favorites = sorted([f.strip() for f in favorites_raw if isinstance(f, str)])

    all_clips_raw = clips_data.get(clip_type_key, [])
    all_clips = sorted([c.strip() for c in all_clips_raw if isinstance(c, str)])

    canonical_options = []
    seen_values = set()

    for fav_clip in favorites:
        if fav_clip not in seen_values:
            canonical_options.append({'label': f"⭐ {fav_clip}", 'value': fav_clip})
            seen_values.add(fav_clip)

    for clip in all_clips:
        if clip not in seen_values:
            canonical_options.append({'label': clip, 'value': clip})
            seen_values.add(clip)

    if current_clip and current_clip not in seen_values:
        is_fav = current_clip in favorites
        label = f"{'⭐ ' if is_fav else ''}{current_clip}".strip()
        canonical_options.insert(0, {'label': label, 'value': current_clip})

    for option_data in canonical_options:
        is_default = (option_data['value'] == current_clip)
        choices.append(discord.SelectOption(label=option_data['label'][:100], value=option_data['value'], default=is_default))

    if choices and not any(opt.default for opt in choices):
        if choices:
            choices[0].default = True

    return choices[:25]


def get_t5_clip_choices(settings): return get_clip_choices(settings, 't5', 'selected_t5_clip')
def get_clip_l_choices(settings): return get_clip_choices(settings, 'clip_L', 'selected_clip_l')


def get_style_choices_flux(settings):
    choices = []; styles = load_styles_config()
    current_style = settings.get('default_style_flux', 'off').strip()
    
    filtered_styles = {name: data for name, data in styles.items() if isinstance(data, dict) and data.get('model_type', 'all') in ['all', 'flux']}

    canonical_options = []
    favorite_styles = []
    other_styles = []
    off_option = None

    for style_raw, data_raw in filtered_styles.items():
        style = style_raw.strip()
        is_favorite = data_raw.get('favorite', False)
        label_prefix = "⭐" if is_favorite and style != "off" else ("🔴" if style == "off" else "")
        option_label = f"{label_prefix} {style}".strip()
        option_data = {'label': option_label, 'value': style}

        if style == 'off':
            off_option = option_data
        elif is_favorite:
            favorite_styles.append(option_data)
        else:
            other_styles.append(option_data)

    favorite_styles.sort(key=lambda o: o['label'].lstrip('⭐🔴 '))
    other_styles.sort(key=lambda o: o['label'])
    
    if off_option:
        canonical_options.append(off_option)
    canonical_options.extend(favorite_styles)
    canonical_options.extend(other_styles)

    for option_data in canonical_options:
        is_default = (option_data['value'] == current_style)
        choices.append(discord.SelectOption(label=option_data['label'][:100], value=option_data['value'], default=is_default))
    
    if choices and not any(opt.default for opt in choices):
        found = False
        for opt in choices:
            if opt.value == current_style:
                opt.default = True
                found = True
                break
        if not found and choices:
            choices[0].default = True

    return choices[:25]


def get_style_choices_sdxl(settings):
    choices = []; styles = load_styles_config()
    current_style = settings.get('default_style_sdxl', 'off').strip()

    filtered_styles = {name: data for name, data in styles.items() if isinstance(data, dict) and data.get('model_type', 'all') in ['all', 'sdxl']}

    canonical_options = []
    favorite_styles = []
    other_styles = []
    off_option = None

    for style_raw, data_raw in filtered_styles.items():
        style = style_raw.strip()
        is_favorite = data_raw.get('favorite', False)
        label_prefix = "⭐" if is_favorite and style != "off" else ("🔴" if style == "off" else "")
        option_label = f"{label_prefix} {style}".strip()
        option_data = {'label': option_label, 'value': style}

        if style == 'off':
            off_option = option_data
        elif is_favorite:
            favorite_styles.append(option_data)
        else:
            other_styles.append(option_data)

    favorite_styles.sort(key=lambda o: o['label'].lstrip('⭐🔴 '))
    other_styles.sort(key=lambda o: o['label'])
    
    if off_option:
        canonical_options.append(off_option)
    canonical_options.extend(favorite_styles)
    canonical_options.extend(other_styles)

    for option_data in canonical_options:
        is_default = (option_data['value'] == current_style)
        choices.append(discord.SelectOption(label=option_data['label'][:100], value=option_data['value'], default=is_default))
    
    if choices and not any(opt.default for opt in choices):
        found = False
        for opt in choices:
            if opt.value == current_style:
                opt.default = True
                found = True
                break
        if not found and choices:
            choices[0].default = True

    return choices[:25]


def get_style_choices_qwen(settings):
    choices = []
    styles = load_styles_config()
    current_style = settings.get('default_style_qwen', 'off')
    if isinstance(current_style, str):
        current_style = current_style.strip()
    else:
        current_style = 'off'

    filtered_styles = {
        name: data
        for name, data in styles.items()
        if isinstance(data, dict) and data.get('model_type', 'all') in ['all', 'qwen']
    }

    canonical_options: list[dict[str, str]] = []
    favorite_styles: list[dict[str, str]] = []
    other_styles: list[dict[str, str]] = []
    off_option: dict[str, str] | None = None

    for style_raw, data_raw in filtered_styles.items():
        style_name = style_raw.strip()
        is_favorite = data_raw.get('favorite', False)
        label_prefix = '⭐' if is_favorite and style_name != 'off' else ('🔴' if style_name == 'off' else '')
        option_label = f"{label_prefix} {style_name}".strip()
        option_data = {'label': option_label, 'value': style_name}

        if style_name == 'off':
            off_option = option_data
        elif is_favorite:
            favorite_styles.append(option_data)
        else:
            other_styles.append(option_data)

    favorite_styles.sort(key=lambda o: o['label'].lstrip('⭐🔴 '))
    other_styles.sort(key=lambda o: o['label'])

    if off_option:
        canonical_options.append(off_option)
    canonical_options.extend(favorite_styles)
    canonical_options.extend(other_styles)

    if current_style and current_style not in {opt['value'] for opt in canonical_options}:
        canonical_options.insert(0, {'label': current_style, 'value': current_style})

    for option_data in canonical_options:
        is_default = option_data['value'] == current_style
        choices.append(
            discord.SelectOption(
                label=option_data['label'][:100],
                value=option_data['value'],
                default=is_default,
            )
        )

    if choices and not any(opt.default for opt in choices):
        for opt in choices:
            if opt.value == current_style:
                opt.default = True
                break
        else:
            choices[0].default = True

    return choices[:25]


def get_steps_choices(settings):
    try: current_steps = int(settings.get('steps', 32))
    except (ValueError, TypeError): current_steps = 32
    steps_options = sorted(list(set([4, 8, 16, 24, 32, 40, 48, 56, 64] + [current_steps])))
    choices = [discord.SelectOption(label=f"{s} Steps", value=str(s), default=(s == current_steps)) for s in steps_options]
    if choices and not any(o.default for o in choices): choices[0].default = True
    return choices[:25] 

def get_sdxl_steps_choices(settings):
    """Creates a list of discord.SelectOption for SDXL steps setting."""
    try:
        current_steps = int(settings.get('sdxl_steps', 26))
    except (ValueError, TypeError):
        current_steps = 26
    steps_options = sorted(list(set([16, 20, 26, 32, 40, 50] + [current_steps])))
    choices = [discord.SelectOption(label=f"{s} Steps (SDXL)", value=str(s), default=(s == current_steps)) for s in steps_options]
    if choices and not any(o.default for o in choices):
        choices[0].default = True
    return choices[:25]

def get_guidance_choices(settings):
    try: current_guidance = float(settings.get('default_guidance', 3.5))
    except (ValueError, TypeError): current_guidance = 3.5
    guidance_values_formatted = [f"{g:.1f}" for g in np.arange(0.0, 10.1, 0.5)]
    current_guidance_str = f"{current_guidance:.1f}"
    if current_guidance_str not in guidance_values_formatted:
        guidance_values_formatted.append(current_guidance_str)
        guidance_values_formatted.sort(key=float)
    choices = [discord.SelectOption(label=f"Guidance (Flux): {g}", value=g, default=(abs(float(g) - current_guidance) < 0.01)) for g in guidance_values_formatted]
    if choices and not any(o.default for o in choices): choices[0].default = True
    return choices[:25]

def get_sdxl_guidance_choices(settings):
    try: current_guidance_sdxl = float(settings.get('default_guidance_sdxl', 7.0))
    except (ValueError, TypeError): current_guidance_sdxl = 7.0
    guidance_values_formatted = [f"{g:.1f}" for g in np.arange(1.0, 15.1, 0.5)]
    current_guidance_sdxl_str = f"{current_guidance_sdxl:.1f}"
    if current_guidance_sdxl_str not in guidance_values_formatted:
        guidance_values_formatted.append(current_guidance_sdxl_str)
        guidance_values_formatted.sort(key=float)
    choices = [discord.SelectOption(label=f"Guidance (SDXL): {g}", value=g, default=(abs(float(g) - current_guidance_sdxl) < 0.01)) for g in guidance_values_formatted]
    if choices and not any(o.default for o in choices): choices[0].default = True
    return choices[:25]

def get_variation_mode_choices(settings):
    current_mode = settings.get('default_variation_mode', 'weak')
    return [discord.SelectOption(label=f"{m.capitalize()} Variation", value=m, default=(m == current_mode)) for m in ["weak", "strong"]]

def get_variation_batch_size_choices(settings):
    """Creates a list of discord.SelectOption for variation batch size."""
    try:
        current_size = int(settings.get('variation_batch_size', 1))
    except (ValueError, TypeError):
        current_size = 1
    return [discord.SelectOption(label=f"Variation Batch Size: {s}", value=str(s), default=(s == current_size)) for s in [1, 2, 3, 4]]

def get_batch_size_choices(settings):
    try: current_size = int(settings.get('default_batch_size', 1))
    except(ValueError, TypeError): current_size = 1
    return [discord.SelectOption(label=f"Batch Size: {s}", value=str(s), default=(s == current_size)) for s in [1, 2, 3, 4]]

def get_remix_mode_choices(settings):
    current_value = settings.get('remix_mode', False)
    return [discord.SelectOption(label="Remix Mode: OFF", value="False", default=not current_value), discord.SelectOption(label="Remix Mode: ON", value="True", default=current_value)]

def get_upscale_factor_choices(settings):
    try: current_factor = float(settings.get('upscale_factor', 1.85))
    except (ValueError, TypeError): current_factor = 1.85
    factor_values_formatted = [f"{f:.2f}" for f in np.arange(1.5, 4.01, 0.25)]
    current_factor_str = f"{current_factor:.2f}"
    if current_factor_str not in factor_values_formatted:
        factor_values_formatted.append(current_factor_str); factor_values_formatted.sort(key=float)
    choices = [discord.SelectOption(label=f"Upscale Factor: {f}x", value=f, default=(abs(float(f) - current_factor) < 0.01)) for f in factor_values_formatted]
    if choices and not any(o.default for o in choices): choices[0].default = True
    return choices[:25]

def get_llm_enhancer_choices(settings):
    current_value = settings.get('llm_enhancer_enabled', False)
    return [discord.SelectOption(label="LLM Prompt Enhancer: OFF", value="False", default=not current_value), discord.SelectOption(label="LLM Prompt Enhancer: ON", value="True", default=current_value)]

def get_llm_provider_choices(settings):
    current_provider = settings.get('llm_provider', 'gemini')
    providers = llm_models_config.get('providers', {})
    options = [discord.SelectOption(label=d.get("display_name", k), value=k, default=(k == current_provider)) for k, d in providers.items()]
    if options and not any(o.default for o in options):
        if any(opt.value == current_provider for opt in options):
            next(opt for opt in options if opt.value == current_provider).default = True
        elif options: options[0].default = True
    return options

def get_llm_model_choices(settings, provider=None):
    if provider is None: provider = settings.get('llm_provider', 'gemini')
    provider_data = llm_models_config.get('providers', {}).get(provider, {})
    models_raw = provider_data.get('models', [])
    models = [m.strip() for m in models_raw if isinstance(m, str)]
    if not models:
         provider_display = provider_data.get("display_name", provider.capitalize())
         return [discord.SelectOption(label=f"No models for {provider_display}", value="none", default=True)]
    current_model_key = f"llm_model_{provider}"; current_model_setting = settings.get(current_model_key)
    current_model = current_model_setting.strip() if isinstance(current_model_setting, str) else None
    
    canonical_options = []
    seen_values = set()
    
    for model in sorted(models):
        if model not in seen_values:
            canonical_options.append({'label': model, 'value': model})
            seen_values.add(model)
            
    if current_model and current_model not in seen_values:
        canonical_options.insert(0, {'label': current_model, 'value': current_model})

    choices = []
    for option_data in canonical_options:
        is_default = (option_data['value'] == current_model)
        choices.append(discord.SelectOption(label=option_data['label'][:100], value=option_data['value'], default=is_default))

    if choices and not any(o.default for o in choices): 
        choices[0].default = True

    return choices[:25]

def get_mp_size_choices(settings):
    try:
        current_size_float = float(settings.get('default_mp_size', 1.0))
    except (ValueError, TypeError):
        current_size_float = 1.0

    allowed_sizes = ["0.25", "0.5", "1.0", "1.25", "1.5", "1.75", "2.0", "2.5", "3.0", "4.0"]
    current_size_str = f"{current_size_float:.2f}".rstrip('0').rstrip('.')
    if current_size_str + ".0" in allowed_sizes: current_size_str += ".0" # Normalize for matching
    if current_size_str not in allowed_sizes:
         allowed_sizes.append(current_size_str)
         allowed_sizes.sort(key=float)

    size_labels = {
        "0.25": "0.25MP (~512x512)", "0.5": "0.5MP (~768x768)", "1.0": "1.0MP (~1024x1024)",
        "1.25": "1.25MP (~1280x1024)", "1.5": "1.5MP (~1440x1024)", "1.75": "1.75MP (~1600x1024)",
        "2.0": "2.0MP (~1920x1080)", "2.5": "2.5MP (~1536x1536)", "3.0": "3.0MP (~1792x1792)", "4.0": "4.0MP (~2048x2048)"
    }
    
    choices = []
    for s in allowed_sizes:
        is_default = abs(float(s) - current_size_float) < 1e-6
        label = size_labels.get(s, f"{s} MP")
        choices.append(discord.SelectOption(label=label, value=s, default=is_default))

    if choices and not any(o.default for o in choices):
        choices[0].default = True

    return choices[:25]


def get_qwen_edit_steps_choices(settings):
    try:
        current_steps = int(settings.get('qwen_edit_steps', 30))
    except (ValueError, TypeError):
        current_steps = 30

    base_options = [20, 24, 30, 36, 40, 48]
    if current_steps not in base_options:
        base_options.append(current_steps)
    base_options = sorted(set(base_options))

    choices = [
        discord.SelectOption(
            label=f"{steps} Steps (Qwen Edit)",
            value=str(steps),
            default=(steps == current_steps),
        )
        for steps in base_options
    ]

    if choices and not any(option.default for option in choices):
        choices[0].default = True

    return choices[:25]


def get_qwen_edit_guidance_choices(settings):
    try:
        current_guidance = float(settings.get('qwen_edit_guidance', 6.0))
    except (ValueError, TypeError):
        current_guidance = 6.0

    guidance_values = [f"{value:.1f}" for value in np.arange(1.0, 15.1, 0.5)]
    current_value = f"{current_guidance:.1f}"
    if current_value not in guidance_values:
        guidance_values.append(current_value)
        guidance_values.sort(key=float)

    choices = [
        discord.SelectOption(
            label=f"Guidance (Qwen Edit): {value}",
            value=value,
            default=abs(float(value) - current_guidance) < 0.05,
        )
        for value in guidance_values
    ]

    if choices and not any(option.default for option in choices):
        choices[0].default = True

    return choices[:25]


def get_qwen_edit_denoise_choices(settings):
    try:
        current_denoise = float(settings.get('qwen_edit_denoise', 0.65))
    except (ValueError, TypeError):
        current_denoise = 0.65

    denoise_values = [f"{value:.2f}" for value in np.arange(0.10, 1.01, 0.05)]
    current_value = f"{current_denoise:.2f}"
    if current_value not in denoise_values:
        denoise_values.append(current_value)
        denoise_values.sort(key=float)

    choices = [
        discord.SelectOption(
            label=f"Denoise (Qwen Edit): {value}",
            value=value,
            default=abs(float(value) - current_denoise) < 0.01,
        )
        for value in denoise_values
    ]

    if choices and not any(option.default for option in choices):
        choices[0].default = True

    return choices[:25]

def get_upscale_model_choices(settings):
    choices = []; models_data = {}; # Changed var name to avoid conflict
    try:
        from comfyui_api import get_available_comfyui_models
        models_data = get_available_comfyui_models(suppress_summary_print=True)
    except Exception: pass
    upscale_models_raw = []
    if isinstance(models_data, dict):
        upscale_models_raw.extend(models_data.get('upscaler', []))
        if not upscale_models_raw: upscale_models_raw.extend(models_data.get('unet', [])) # Fallback
    upscale_models = sorted(list(set(u.strip() for u in upscale_models_raw if isinstance(u, str))))
    current_upscale_model_setting = settings.get('selected_upscale_model')
    current_upscale_model = current_upscale_model_setting.strip() if isinstance(current_upscale_model_setting, str) else None
    
    canonical_options = []
    seen_values = set()
    for model in upscale_models:
        if model not in seen_values:
            canonical_options.append({'label': model, 'value': model})
            seen_values.add(model)
            
    if current_upscale_model and current_upscale_model not in seen_values:
        label = f"{current_upscale_model} (Custom?)"
        canonical_options.insert(0, {'label': label, 'value': current_upscale_model})
    
    for option_data in canonical_options:
        is_default = (option_data['value'] == current_upscale_model)
        choices.append(discord.SelectOption(label=option_data['label'][:100], value=option_data['value'], default=is_default))

    if not choices: choices.append(discord.SelectOption(label="None Available/Selected", value="None", default=True if not current_upscale_model else False))
    elif choices and not any(c.default for c in choices): choices[0].default = True
    return choices[:25]


def get_vae_choices(settings):
    choices = []; models_data = {} # Changed var name
    try:
        from comfyui_api import get_available_comfyui_models
        models_data = get_available_comfyui_models(suppress_summary_print=True)
    except Exception: pass
    vae_models_raw = models_data.get('vae', []) if isinstance(models_data, dict) else []
    vae_models = sorted(list(set(v.strip() for v in vae_models_raw if isinstance(v, str))))
    current_vae_setting = settings.get('selected_vae')
    current_vae = current_vae_setting.strip() if isinstance(current_vae_setting, str) else None
    
    canonical_options = []
    seen_values = set()
    for vae in vae_models:
        if vae not in seen_values:
            canonical_options.append({'label': vae, 'value': vae})
            seen_values.add(vae)
            
    if current_vae and current_vae not in seen_values:
        label = f"{current_vae} (Custom?)"
        canonical_options.insert(0, {'label': label, 'value': current_vae})
    
    for option_data in canonical_options:
        is_default = (option_data['value'] == current_vae)
        choices.append(discord.SelectOption(label=option_data['label'][:100], value=option_data['value'], default=is_default))

    if not choices: choices.append(discord.SelectOption(label="None Available/Selected", value="None", default=True if not current_vae else False))
    elif choices and not any(c.default for c in choices): choices[0].default = True
    return choices[:25]

def get_display_prompt_preference_choices(settings):
    current_preference = settings.get('display_prompt_preference', 'enhanced')
    return [discord.SelectOption(label="Show Enhanced Prompt ✨", value="enhanced", default=(current_preference == 'enhanced')), discord.SelectOption(label="Show Original Prompt ✍️", value="original", default=(current_preference == 'original'))]

def get_kontext_model_choices(settings):
    choices = []
    flux_models_data = {}
    try:
        if os.path.exists('modelslist.json'):
            with open('modelslist.json', 'r') as f: flux_models_data = json.load(f)
        if not isinstance(flux_models_data, dict): flux_models_data = {}
    except Exception: flux_models_data = {}

    current_kontext_model = settings.get('selected_kontext_model')
    if isinstance(current_kontext_model, str): current_kontext_model = current_kontext_model.strip()

    flux_favorites_raw = flux_models_data.get('favorites', [])
    flux_favorites = [f.strip() for f in flux_favorites_raw if isinstance(f, str)]
    
    canonical_options = []
    seen_values = set()
    
    for model in sorted(flux_favorites):
        if model not in seen_values:
            canonical_options.append({'label': f"⭐ {model}", 'value': model})
            seen_values.add(model)
            
    all_flux_models_raw = []
    for model_type_key in ['safetensors', 'sft', 'gguf']:
        all_flux_models_raw.extend(flux_models_data.get(model_type_key, []))
    
    for model in sorted(list(set(m.strip() for m in all_flux_models_raw if isinstance(m, str)))):
        if model not in seen_values:
            canonical_options.append({'label': model, 'value': model})
            seen_values.add(model)
            
    if current_kontext_model and current_kontext_model not in seen_values:
        is_fav = current_kontext_model in flux_favorites
        label = f"{'⭐ ' if is_fav else ''}{current_kontext_model}".strip()
        canonical_options.insert(0, {'label': label, 'value': current_kontext_model})

    for option_data in canonical_options:
        is_default = (option_data['value'] == current_kontext_model)
        choices.append(discord.SelectOption(label=option_data['label'][:100], value=option_data['value'], default=is_default))
        
    if choices and not any(opt.default for opt in choices):
        choices[0].default = True

    return choices[:25]
# --- END OF FILE settings_manager.py ---
