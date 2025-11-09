# --- START OF FILE settings_manager.py ---
# START OF FILE settings_manager.py

import json
import discord
import os
import numpy as np
import traceback
from typing import Dict, Iterable, List, Optional, Tuple

from settings_shared import (
    WAN_CHECKPOINT_KEY,
    WAN_I2V_HIGH_NOISE_KEY,
    WAN_I2V_LOW_NOISE_KEY,
    WAN_T2V_HIGH_NOISE_KEY,
    WAN_T2V_LOW_NOISE_KEY,
    sync_wan_checkpoint_alias,
)

from model_registry import get_model_spec, resolve_model_type_from_prefix


KSAMPLER_SAMPLER_OPTIONS = [
    "euler",
    "euler_ancestral",
    "heun",
    "heunpp2",
    "dpm_2",
    "dpm_2_ancestral",
    "lms",
    "dpm_fast",
    "dpm_adaptive",
    "dpmpp_2s_ancestral",
    "dpmpp_2s_ancestral_cfg_pp",
    "dpmpp_sde",
    "dpmpp_sde_gpu",
    "dpmpp_2m",
    "dpmpp_2m_cfg_pp",
    "dpmpp_2m_sde",
    "dpmpp_2m_sde_gpu",
    "dpmpp_2m_sde_heun",
    "dpmpp_2m_sde_heun_gpu",
    "dpmpp_3m_sde",
    "dpmpp_3m_sde_gpu",
    "ddpm",
    "lcm",
    "ipndm",
    "ipndm_v",
    "deis",
    "res_multistep",
    "res_multistep_cfg_pp",
    "res_multistep_ancestral",
    "res_multistep_ancestral_cfg_pp",
    "gradient_estimation",
    "gradient_estimation_cfg_pp",
    "er_sde",
    "seeds_2",
    "seeds_3",
    "sa_solver",
    "sa_solver_pece",
]

KSAMPLER_SCHEDULER_OPTIONS = [
    "simple",
    "sgm_uniform",
    "karras",
    "exponential",
    "ddim_uniform",
    "beta",
    "normal",
    "linear_quadratic",
    "kl_optimal",
]


MODEL_SELECTION_PREFIX = {
    "flux": "Flux",
    "sdxl": "SDXL",
    "qwen": "Qwen",
    "qwen_edit": "Qwen Edit",
    "wan": "WAN",
}

GENERATION_MODEL_FAMILIES = ("flux", "sdxl", "qwen", "qwen_edit", "wan")


def _format_prefixed_model_name(model_family: str, model_name: Optional[str]) -> Optional[str]:
    """Return a canonical "Prefix: Model" string for the active family."""

    if not model_name:
        return None

    prefix_label = MODEL_SELECTION_PREFIX.get(model_family)
    if not prefix_label:
        return None

    cleaned_name = model_name.strip()
    if not cleaned_name:
        return None

    return f"{prefix_label}: {cleaned_name}"


def sync_active_model_selection(settings: dict, *, active_family: Optional[str] = None) -> None:
    """Ensure the `selected_model` matches the configured active family default."""

    if not isinstance(settings, dict):
        return

    family_key = active_family or str(settings.get("active_model_family", "flux") or "flux").lower()
    default_map = {
        "flux": "default_flux_model",
        "sdxl": "default_sdxl_checkpoint",
        "qwen": "default_qwen_checkpoint",
        "qwen_edit": "default_qwen_edit_checkpoint",
        "wan": WAN_T2V_HIGH_NOISE_KEY,
    }

    default_key = default_map.get(family_key)
    if not default_key:
        settings["selected_model"] = None
        return

    selected_default = settings.get(default_key)
    formatted = _format_prefixed_model_name(family_key, selected_default if isinstance(selected_default, str) else None)
    settings["selected_model"] = formatted

MODEL_CATALOG_FILES = {
    "flux": "modelslist.json",
    "sdxl": "checkpointslist.json",
    "qwen": "qwenmodels.json",
    "qwen_edit": "qweneditmodels.json",
    "wan": "wanmodels.json",
}

STYLE_FILTERS = {
    "flux": {"all", "flux"},
    "sdxl": {"all", "sdxl"},
    "qwen": {"all", "qwen"},
    "qwen_edit": {"all", "qwen", "qwen_edit"},
    "wan": {"all", "wan"},
}

DEFAULT_STEP_OPTIONS = {
    "flux": [4, 8, 16, 24, 32, 40, 48, 56, 64],
    "sdxl": [16, 20, 26, 32, 40, 50],
    "qwen": [12, 16, 20, 24, 28, 32, 36, 40],
    "qwen_edit": [12, 16, 20, 24, 28, 32, 36, 40],
    "wan": [12, 18, 24, 30, 36, 42, 50],
}

GUIDANCE_CONFIG = {
    "flux": {"start": 0.0, "stop": 10.0, "step": 0.5},
    "sdxl": {"start": 1.0, "stop": 15.0, "step": 0.5},
    "qwen": {"start": 0.0, "stop": 10.0, "step": 0.5},
    "qwen_edit": {"start": 0.0, "stop": 10.0, "step": 0.5},
    "wan": {"start": 1.0, "stop": 15.0, "step": 0.5},
}

def load_llm_models_config():
    default_config = {
        "providers": {
            "gemini": {
                "display_name": "Google Gemini API",
                "models": ["gemini-1.5-flash"],
                "favorites": []
            },
            "groq": {
                "display_name": "Groq API",
                "models": ["llama3-8b-8192"],
                "favorites": []
            },
            "openai": {
                "display_name": "OpenAI API",
                "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                "favorites": []
            }
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

        for key, data in list(config["providers"].items()):
            if not isinstance(data, dict) or "display_name" not in data or "models" not in data or not isinstance(data["models"], list):
                print(f"SettingsManager Warning: Invalid structure for provider '{key}'. Reverting to default for this provider.")
                # Use .get for safer access to default_config in case a new provider was added manually but is malformed
                config["providers"][key] = default_config["providers"].get(
                    key,
                    {"display_name": key, "models": [], "favorites": []}
                )
                data = config["providers"][key]
            if "favorites" not in data or not isinstance(data.get("favorites"), list):
                data["favorites"] = []
            else:
                data["favorites"] = [
                    str(model_name).strip()
                    for model_name in data["favorites"]
                    if isinstance(model_name, str)
                ]
            data["models"] = [
                str(model_name).strip()
                for model_name in data.get("models", [])
                if isinstance(model_name, str)
            ]
            config["providers"][key] = data
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


def _extract_catalog_entries(raw_data: object, *, favorites_key: str = "favorites") -> Tuple[List[str], List[str]]:
    favorites: List[str] = []
    items: List[str] = []

    if isinstance(raw_data, dict):
        raw_favorites = raw_data.get(favorites_key)
        if isinstance(raw_favorites, dict):
            for value in raw_favorites.values():
                if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                    favorites.extend(str(v).strip() for v in value if isinstance(v, str) and v.strip())
        elif isinstance(raw_favorites, Iterable) and not isinstance(raw_favorites, (str, bytes)):
            favorites.extend(str(v).strip() for v in raw_favorites if isinstance(v, str) and v.strip())

        for key, value in raw_data.items():
            if key == favorites_key:
                continue
            if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                items.extend(str(v).strip() for v in value if isinstance(v, str) and v.strip())
    elif isinstance(raw_data, Iterable) and not isinstance(raw_data, (str, bytes)):
        items.extend(str(v).strip() for v in raw_data if isinstance(v, str) and v.strip())

    # Remove duplicates while preserving order
    seen: set[str] = set()
    deduped_items: List[str] = []
    for entry in items:
        if entry and entry not in seen:
            deduped_items.append(entry)
            seen.add(entry)

    seen_favorites: set[str] = set()
    deduped_favorites: List[str] = []
    for fav in favorites:
        if fav and fav not in seen_favorites:
            deduped_favorites.append(fav)
            seen_favorites.add(fav)

    return deduped_favorites, deduped_items


def _load_model_catalog(file_name: str) -> Tuple[List[str], List[str]]:
    if not file_name:
        return [], []

    try:
        if not os.path.exists(file_name):
            return [], []
        with open(file_name, 'r') as f:
            raw_data = json.load(f)
    except Exception as exc:
        print(f"Warning: Could not load {file_name}: {exc}")
        return [], []

    return _extract_catalog_entries(raw_data)


def _get_first_model_from_catalog(model_type: str) -> Optional[str]:
    file_name = MODEL_CATALOG_FILES.get(model_type)
    if not file_name:
        return None

    favorites, items = _load_model_catalog(file_name)
    if favorites:
        return favorites[0]
    if items:
        return items[0]
    return None


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

        legacy_cfg_pairs = (
            ("qwen_ksampler_cfg", "default_guidance_qwen"),
            ("qwen_edit_ksampler_cfg", "default_guidance_qwen_edit"),
        )
        for legacy_key, guidance_key in legacy_cfg_pairs:
            if legacy_key in settings:
                legacy_value = settings.pop(legacy_key)
                try:
                    coerced = float(legacy_value)
                except (TypeError, ValueError):
                    coerced = None
                if coerced is not None:
                    current_guidance = settings.get(guidance_key)
                    if current_guidance in (None, "") or current_guidance == default_settings.get(guidance_key):
                        settings[guidance_key] = coerced
                updated = True
        for key, default_value in default_settings.items():
            if key not in settings:
                print(f"Warning: Setting '{key}' missing. Adding default value: {default_value}")
                settings[key] = default_value
                updated = True

        numeric_keys_float = [
            'default_guidance',
            'default_guidance_sdxl',
            'default_guidance_qwen',
            'default_guidance_qwen_edit',
            'default_guidance_wan',
            'upscale_factor',
            'default_mp_size',
            'kontext_guidance',
            'kontext_mp_size',
            'default_qwen_shift',
            'default_wan_shift',
            'qwen_edit_denoise',
            'qwen_edit_shift',
            'flux_ksampler_cfg',
            'flux_ksampler_denoise',
            'sdxl_ksampler_cfg',
            'sdxl_ksampler_denoise',
            'qwen_ksampler_denoise',
            'qwen_edit_ksampler_denoise',
            'qwen_edit_cfg_rescale',
            'wan_stage1_cfg',
            'wan_stage1_denoise',
            'wan_stage2_cfg',
            'wan_stage2_denoise',
            'flux_upscale_cfg',
            'flux_upscale_denoise',
            'sdxl_upscale_cfg',
            'sdxl_upscale_denoise',
            'qwen_upscale_cfg',
            'qwen_upscale_denoise',
        ]
        float_bounds = {
            'default_qwen_shift': (0.0, 10.0),
            'qwen_edit_shift': (0.0, 10.0),
            'default_wan_shift': (0.0, 10.0),
            'qwen_edit_denoise': (0.0, 1.0),
            'flux_ksampler_denoise': (0.0, 1.0),
            'sdxl_ksampler_denoise': (0.0, 1.0),
            'qwen_ksampler_denoise': (0.0, 1.0),
            'qwen_edit_ksampler_denoise': (0.0, 1.0),
            'qwen_edit_cfg_rescale': (0.0, 2.0),
            'wan_stage1_denoise': (0.0, 1.0),
            'wan_stage2_denoise': (0.0, 1.0),
            'flux_upscale_denoise': (0.0, 1.0),
            'sdxl_upscale_denoise': (0.0, 1.0),
            'qwen_upscale_denoise': (0.0, 1.0),
        }
        numeric_keys_int = [
            'steps',
            'sdxl_steps',
            'qwen_steps',
            'qwen_edit_steps',
            'wan_steps',
            'default_batch_size',
            'kontext_steps',
            'variation_batch_size',
            'wan_animation_duration',
            'wan_stage1_noise_seed',
            'wan_stage1_seed',
            'wan_stage1_steps',
            'wan_stage1_start',
            'wan_stage1_end',
            'wan_stage2_noise_seed',
            'wan_stage2_seed',
            'wan_stage2_steps',
            'wan_stage2_start',
            'wan_stage2_end',
            'flux_upscale_steps',
            'sdxl_upscale_steps',
            'qwen_upscale_steps',
        ]
        bool_keys = ['remix_mode', 'llm_enhancer_enabled']
        display_prompt_key = 'display_prompt_preference'
        allowed_display_prompt_options = ['enhanced', 'original']


        for key in numeric_keys_float:
            if key in settings:
                try:
                    if settings[key] is None:
                        continue
                    coerced_val = float(settings[key])
                except (ValueError, TypeError):
                    print(f"Warning: Setting '{key}' has invalid type ({type(settings[key])}). Resetting to default.")
                    coerced_val = float(default_settings[key])
                    updated = True

                bounds = float_bounds.get(key)
                if bounds:
                    min_val, max_val = bounds
                    if coerced_val < min_val:
                        coerced_val = min_val
                        updated = True
                    if coerced_val > max_val:
                        coerced_val = max_val
                        updated = True

                settings[key] = coerced_val

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


        llm_string_keys = ['llm_provider', 'llm_model_gemini', 'llm_model_groq', 'llm_model_openai', 'wan_animation_motion_profile', 'wan_animation_resolution', 'active_model_family']
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

        allowed_motion_profiles = {'slowmo', 'low', 'medium', 'high'}
        motion_profile = str(settings.get('wan_animation_motion_profile', default_settings['wan_animation_motion_profile'])).lower()
        if motion_profile not in allowed_motion_profiles:
            print(f"Warning: WAN motion profile '{motion_profile}' invalid. Using default.")
            settings['wan_animation_motion_profile'] = default_settings['wan_animation_motion_profile']
            updated = True
        else:
            settings['wan_animation_motion_profile'] = motion_profile

        resolution_value = str(settings.get('wan_animation_resolution', default_settings['wan_animation_resolution'])).lower()
        try:
            width_str, height_str = resolution_value.split('x', 1)
            width_val = int(width_str)
            height_val = int(height_str)
            if width_val <= 0 or height_val <= 0:
                raise ValueError
            settings['wan_animation_resolution'] = f"{width_val}x{height_val}"
        except (ValueError, AttributeError):
            print(f"Warning: WAN animation resolution '{resolution_value}' invalid. Using default.")
            settings['wan_animation_resolution'] = default_settings['wan_animation_resolution']
            updated = True

        try:
            duration_val = int(settings.get('wan_animation_duration', default_settings['wan_animation_duration']))
            if duration_val < 8:
                duration_val = 8
            elif duration_val > 240:
                duration_val = 240
            settings['wan_animation_duration'] = duration_val
        except (ValueError, TypeError):
            print("Warning: WAN animation duration invalid. Using default.")
            settings['wan_animation_duration'] = default_settings['wan_animation_duration']
            updated = True

        allowed_families = set(GENERATION_MODEL_FAMILIES)
        active_family = str(settings.get('active_model_family', default_settings['active_model_family'])).lower()
        if active_family not in allowed_families:
            print(f"Warning: Active model family '{active_family}' invalid. Using default.")
            settings['active_model_family'] = default_settings['active_model_family']
            updated = True
        else:
            settings['active_model_family'] = active_family

        edit_mode_raw = str(settings.get('default_editing_mode', default_settings['default_editing_mode']) or default_settings['default_editing_mode']).lower()
        qwen_edit_aliases = {'qwen_edit', 'qwen', 'qwen-image-edit', 'qwen_image_edit', 'qwenedit'}
        kontext_aliases = {'kontext', 'kontext_edit', 'kontext-edit'}
        if edit_mode_raw in qwen_edit_aliases:
            normalized_edit_mode = 'qwen_edit'
        elif edit_mode_raw in kontext_aliases:
            normalized_edit_mode = 'kontext'
        else:
            print(f"Warning: Editing mode '{edit_mode_raw}' invalid. Using default.")
            normalized_edit_mode = default_settings['default_editing_mode']
        if normalized_edit_mode != edit_mode_raw:
            updated = True
        settings['default_editing_mode'] = normalized_edit_mode

        allowed_providers = list(llm_models_config.get('providers', {}).keys())
        if not allowed_providers: allowed_providers = ['gemini'] # Fallback
        if settings.get('llm_provider') not in allowed_providers:
            print(f"Warning: Invalid 'llm_provider' value '{settings.get('llm_provider')}'. Resetting to default '{default_settings['llm_provider']}'.")
            settings['llm_provider'] = default_settings['llm_provider']
            updated = True

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


        available_qwen_models_raw = []
        try:
            if os.path.exists('qwenmodels.json'):
                with open('qwenmodels.json', 'r') as f: qwen_models_data = json.load(f)
                if isinstance(qwen_models_data, dict):
                    qwen_list = qwen_models_data.get('checkpoints', [])
                    if isinstance(qwen_list, list):
                        available_qwen_models_raw.extend([m for m in qwen_list if isinstance(m, str)])
                    available_qwen_models_raw = list(set(available_qwen_models_raw))
        except Exception as e:
            print(f"Warning: Could not load qwenmodels.json for Qwen model validation: {e}")
        available_qwen_models = {m.strip().lower(): m.strip() for m in available_qwen_models_raw}

        available_qwen_edit_models_raw = []
        try:
            if os.path.exists('qweneditmodels.json'):
                with open('qweneditmodels.json', 'r') as f:
                    qwen_edit_models_data = json.load(f)
                if isinstance(qwen_edit_models_data, dict):
                    edit_list = qwen_edit_models_data.get('checkpoints', [])
                    if isinstance(edit_list, list):
                        available_qwen_edit_models_raw.extend([m for m in edit_list if isinstance(m, str)])
                    available_qwen_edit_models_raw = list(set(available_qwen_edit_models_raw))
        except Exception as e:
            print(f"Warning: Could not load qweneditmodels.json for Qwen Edit model validation: {e}")
        available_qwen_edit_models = {m.strip().lower(): m.strip() for m in available_qwen_edit_models_raw}

        available_wan_models_raw = []
        try:
            if os.path.exists('wanmodels.json'):
                with open('wanmodels.json', 'r') as f: wan_models_data = json.load(f)
                if isinstance(wan_models_data, dict):
                    wan_list = wan_models_data.get('checkpoints', [])
                    if isinstance(wan_list, list):
                        available_wan_models_raw.extend([m for m in wan_list if isinstance(m, str)])
                    available_wan_models_raw = list(set(available_wan_models_raw))
        except Exception as e:
            print(f"Warning: Could not load wanmodels.json for WAN model validation: {e}")
        available_wan_models = {m.strip().lower(): m.strip() for m in available_wan_models_raw}


        model_catalogs = {
            'flux': available_flux_models,
            'sdxl': available_sdxl_checkpoints,
            'qwen': available_qwen_models,
            'qwen_edit': available_qwen_edit_models,
            'wan': available_wan_models,
        }

        fallback_key_map = {
            'flux': 'default_flux_model',
            'sdxl': 'default_sdxl_checkpoint',
            'qwen': 'default_qwen_checkpoint',
            'qwen_edit': 'default_qwen_edit_checkpoint',
            'wan': WAN_T2V_HIGH_NOISE_KEY,
        }

        for family_key, default_key in fallback_key_map.items():
            catalog = model_catalogs.get(family_key) or {}
            current_default = settings.get(default_key)
            if isinstance(current_default, str) and current_default.strip().lower() in catalog:
                corrected = catalog[current_default.strip().lower()]
                if corrected != current_default:
                    settings[default_key] = corrected
                    updated = True
                continue
            if catalog:
                fallback_model = next(iter(catalog.values()))
                if fallback_model != current_default:
                    settings[default_key] = fallback_model
                    updated = True

        sync_active_model_selection(settings)

        current_selected_model_setting = settings.get('selected_model')
        if current_selected_model_setting and isinstance(current_selected_model_setting, str):
            current_model_setting_stripped = current_selected_model_setting.strip()
            model_type, model_name_from_setting = resolve_model_type_from_prefix(current_model_setting_stripped)
            if model_type in model_catalogs:
                catalog = model_catalogs[model_type]
                if model_name_from_setting and model_name_from_setting.lower() in catalog:
                    corrected_name = catalog[model_name_from_setting.lower()]
                    formatted = _format_prefixed_model_name(model_type, corrected_name)
                    if formatted and formatted != settings['selected_model']:
                        settings['selected_model'] = formatted
                        updated = True
                elif catalog:
                    fallback_model = next(iter(catalog.values()))
                    settings[fallback_key_map[model_type]] = fallback_model
                    settings['selected_model'] = _format_prefixed_model_name(model_type, fallback_model)
                    updated = True
            else:
                print(f"⚠️ Warning: Selected model '{current_selected_model_setting}' not recognized. Resetting to active family.")
                sync_active_model_selection(settings)
                updated = True
        else:
            sync_active_model_selection(settings)
            
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
        elif 'default_sdxl_negative_prompt' not in settings: # Ensure key exists
            settings['default_sdxl_negative_prompt'] = default_settings['default_sdxl_negative_prompt']
            updated = True

        for neg_key in ('default_qwen_negative_prompt', 'default_qwen_edit_negative_prompt', 'default_wan_negative_prompt'):
            if neg_key in settings:
                value = settings[neg_key]
                if value is None:
                    settings[neg_key] = ""
                    updated = True
                elif isinstance(value, str):
                    stripped = value.strip()
                    if stripped != value:
                        settings[neg_key] = stripped
                        updated = True
                else:
                    settings[neg_key] = str(value)
                    updated = True
            else:
                settings[neg_key] = default_settings[neg_key]
                updated = True

        previous_alias_state = (
            settings.get(WAN_T2V_HIGH_NOISE_KEY),
            settings.get(WAN_CHECKPOINT_KEY),
        )
        sync_wan_checkpoint_alias(settings)
        if previous_alias_state != (
            settings.get(WAN_T2V_HIGH_NOISE_KEY),
            settings.get(WAN_CHECKPOINT_KEY),
        ):
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
    default_flux_model_raw = _get_first_model_from_catalog("flux")
    default_sdxl_checkpoint_raw = _get_first_model_from_catalog("sdxl")
    default_qwen_checkpoint_raw = _get_first_model_from_catalog("qwen")
    default_qwen_edit_checkpoint_raw = _get_first_model_from_catalog("qwen_edit")
    default_wan_checkpoint_raw = _get_first_model_from_catalog("wan")

    default_model_setting = None
    if default_flux_model_raw:
        default_model_setting = f"{MODEL_SELECTION_PREFIX['flux']}: {default_flux_model_raw}"
    elif default_qwen_checkpoint_raw:
        default_model_setting = f"{MODEL_SELECTION_PREFIX['qwen']}: {default_qwen_checkpoint_raw}"
    elif default_qwen_edit_checkpoint_raw:
        default_model_setting = f"{MODEL_SELECTION_PREFIX['qwen_edit']}: {default_qwen_edit_checkpoint_raw}"
    elif default_wan_checkpoint_raw:
        default_model_setting = f"{MODEL_SELECTION_PREFIX['wan']}: {default_wan_checkpoint_raw}"
    elif default_sdxl_checkpoint_raw:
        default_model_setting = f"{MODEL_SELECTION_PREFIX['sdxl']}: {default_sdxl_checkpoint_raw}"

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

    defaults = {
        "selected_model": default_model_setting,
        "selected_kontext_model": default_flux_model_raw,
        "default_flux_model": default_flux_model_raw,
        "default_flux_vae": None,
        "default_sdxl_checkpoint": default_sdxl_checkpoint_raw,
        "default_sdxl_clip": None,
        "default_sdxl_vae": None,
        "default_qwen_checkpoint": default_qwen_checkpoint_raw,
        "default_qwen_clip": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
        "default_qwen_vae": "qwen_image_vae.safetensors",
        "default_qwen_shift": 0.0,
        "default_qwen_edit_checkpoint": default_qwen_edit_checkpoint_raw,
        "default_qwen_edit_clip": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
        "default_qwen_edit_vae": "qwen_image_vae.safetensors",
        "default_guidance_qwen_edit": 2.5,
        "qwen_edit_steps": 28,
        WAN_CHECKPOINT_KEY: default_wan_checkpoint_raw,
        WAN_T2V_HIGH_NOISE_KEY: default_wan_checkpoint_raw
        or "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
        "default_wan_t2v_low_noise_unet": "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors",
        "default_wan_i2v_high_noise_unet": "wan2.2_i2v_high_noise_14B_fp16.safetensors",
        "default_wan_i2v_low_noise_unet": "wan2.2_i2v_low_noise_14B_fp16.safetensors",
        "default_wan_low_noise_unet": "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors",
        "default_wan_clip": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "default_wan_vae": "wan2.2_vae.safetensors",
        "default_wan_vision_clip": "clip_vision_h.safetensors",
        "default_wan_shift": 8.0,
        "steps": 32,
        "sdxl_steps": 26,
        "qwen_steps": 28,
        "wan_steps": 30,
        "selected_t5_clip": default_t5,
        "selected_clip_l": default_l,
        "flux_ksampler_sampler": "euler",
        "flux_ksampler_scheduler": "sgm_uniform",
        "flux_ksampler_cfg": 1.0,
        "flux_ksampler_denoise": 1.0,
        "sdxl_ksampler_sampler": "euler_ancestral",
        "sdxl_ksampler_scheduler": "normal",
        "sdxl_ksampler_cfg": 6.0,
        "sdxl_ksampler_denoise": 1.0,
        "qwen_ksampler_sampler": "euler",
        "qwen_ksampler_scheduler": "normal",
        "qwen_ksampler_denoise": 1.0,
        "qwen_edit_ksampler_sampler": "euler",
        "qwen_edit_ksampler_scheduler": "normal",
        "qwen_edit_ksampler_denoise": 0.6,
        "wan_stage1_add_noise": "enable",
        "wan_stage1_noise_mode": "randomize",
        "wan_stage1_noise_seed": 8640317771124281,
        "wan_stage1_seed": 8640317771124281,
        "wan_stage1_steps": 20,
        "wan_stage1_cfg": 3.5,
        "wan_stage1_sampler": "euler",
        "wan_stage1_scheduler": "simple",
        "wan_stage1_start": 0,
        "wan_stage1_end": 10,
        "wan_stage1_return_with_leftover_noise": "disable",
        "wan_stage1_denoise": 1.0,
        "wan_stage2_add_noise": "disable",
        "wan_stage2_noise_mode": "fixed",
        "wan_stage2_noise_seed": 0,
        "wan_stage2_seed": 0,
        "wan_stage2_steps": 20,
        "wan_stage2_cfg": 3.5,
        "wan_stage2_sampler": "euler",
        "wan_stage2_scheduler": "simple",
        "wan_stage2_start": 0,
        "wan_stage2_end": 100,
        "wan_stage2_return_with_leftover_noise": "disable",
        "wan_stage2_denoise": 1.0,
        "flux_upscale_model": None,
        "flux_upscale_sampler": "euler",
        "flux_upscale_scheduler": "sgm_uniform",
        "flux_upscale_steps": 16,
        "flux_upscale_cfg": 1.0,
        "flux_upscale_denoise": 0.2,
        "sdxl_upscale_model": None,
        "sdxl_upscale_sampler": "euler_ancestral",
        "sdxl_upscale_scheduler": "normal",
        "sdxl_upscale_steps": 16,
        "sdxl_upscale_cfg": 6.0,
        "sdxl_upscale_denoise": 0.15,
        "qwen_upscale_model": None,
        "qwen_upscale_sampler": "euler",
        "qwen_upscale_scheduler": "normal",
        "qwen_upscale_steps": 16,
        "qwen_upscale_cfg": 2.5,
        "qwen_upscale_denoise": 0.2,
        "selected_vae": None,
        "default_style_flux": "off",
        "default_style_sdxl": "off",
        "default_style_qwen": "off",
        "default_style_wan": "off",
        "default_variation_mode": "weak",
        "variation_batch_size": 1,
        "default_batch_size": 1,
        "default_guidance": 3.5,
        "default_guidance_sdxl": 7.0,
        "default_guidance_qwen": 2.5,
        "default_guidance_wan": 6.0,
        "default_sdxl_negative_prompt": "",
        "default_qwen_negative_prompt": "",
        "default_qwen_edit_negative_prompt": "",
        "default_wan_negative_prompt": "",
        "default_mp_size": 1.0,
        "qwen_edit_denoise": 0.6,
        "qwen_edit_shift": 0.0,
        "qwen_edit_cfg_rescale": 1.0,
        "kontext_guidance": 3.0,
        "kontext_steps": 32,
        "kontext_mp_size": 1.15,
        "remix_mode": False,
        "upscale_factor": 1.85,
        "llm_enhancer_enabled": False,
        "llm_provider": "gemini",
        "llm_model_gemini": default_gemini_model_raw.strip() if default_gemini_model_raw else "gemini-1.5-flash",
        "llm_model_groq": default_groq_model_raw.strip() if default_groq_model_raw else "llama3-8b-8192",
        "llm_model_openai": default_openai_model_raw.strip() if default_openai_model_raw else "gpt-3.5-turbo",
        "display_prompt_preference": "enhanced",
        "default_editing_mode": "kontext",
        "wan_animation_resolution": "512x512",
        "wan_animation_duration": 33,
        "wan_animation_motion_profile": "medium",
        "active_model_family": "flux",
    }

    sync_wan_checkpoint_alias(defaults)
    return defaults

def save_settings(settings):
    settings_file = 'settings.json'
    try:
        numeric_keys_float = [
            'default_guidance',
            'default_guidance_sdxl',
            'default_guidance_qwen',
            'default_guidance_qwen_edit',
            'default_guidance_wan',
            'upscale_factor',
            'default_mp_size',
            'kontext_guidance',
            'kontext_mp_size',
            'default_qwen_shift',
            'default_wan_shift',
            'qwen_edit_denoise',
            'qwen_edit_shift',
            'flux_ksampler_cfg',
            'flux_ksampler_denoise',
            'sdxl_ksampler_cfg',
            'sdxl_ksampler_denoise',
            'qwen_ksampler_denoise',
            'qwen_edit_ksampler_denoise',
            'wan_stage1_cfg',
            'wan_stage1_denoise',
            'wan_stage2_cfg',
            'wan_stage2_denoise',
            'flux_upscale_cfg',
            'flux_upscale_denoise',
            'sdxl_upscale_cfg',
            'sdxl_upscale_denoise',
            'qwen_upscale_cfg',
            'qwen_upscale_denoise',
        ]
        float_bounds = {
            'default_qwen_shift': (0.0, 10.0),
            'qwen_edit_shift': (0.0, 10.0),
            'default_wan_shift': (0.0, 10.0),
            'qwen_edit_denoise': (0.0, 1.0),
            'flux_ksampler_denoise': (0.0, 1.0),
            'sdxl_ksampler_denoise': (0.0, 1.0),
            'qwen_ksampler_denoise': (0.0, 1.0),
            'qwen_edit_ksampler_denoise': (0.0, 1.0),
            'wan_stage1_denoise': (0.0, 1.0),
            'wan_stage2_denoise': (0.0, 1.0),
            'flux_upscale_denoise': (0.0, 1.0),
            'sdxl_upscale_denoise': (0.0, 1.0),
            'qwen_upscale_denoise': (0.0, 1.0),
        }
        numeric_keys_int = [
            'steps', 'sdxl_steps', 'qwen_steps', 'qwen_edit_steps', 'wan_steps', 'default_batch_size',
            'kontext_steps', 'variation_batch_size', 'wan_animation_duration',
            'wan_stage1_noise_seed', 'wan_stage1_seed', 'wan_stage1_steps', 'wan_stage1_start', 'wan_stage1_end',
            'wan_stage2_noise_seed', 'wan_stage2_seed', 'wan_stage2_steps', 'wan_stage2_start', 'wan_stage2_end',
            'flux_upscale_steps', 'sdxl_upscale_steps', 'qwen_upscale_steps'
        ]
        bool_keys = ['remix_mode', 'llm_enhancer_enabled']
        string_keys_to_strip = [
            'llm_provider', 'llm_model_gemini', 'llm_model_groq', 'llm_model_openai',
            'selected_model', 'selected_t5_clip', 'selected_clip_l',
            'selected_vae', 'default_style_flux', 'default_style_sdxl', 'default_style_qwen', 'default_style_wan',
            'default_sdxl_negative_prompt', 'default_qwen_negative_prompt', 'default_qwen_edit_negative_prompt', 'default_wan_negative_prompt',
            'selected_kontext_model', 'default_flux_model', 'default_sdxl_checkpoint', 'default_qwen_checkpoint', 'default_qwen_edit_checkpoint', 'default_wan_checkpoint',
            'default_flux_vae', 'default_sdxl_clip', 'default_sdxl_vae', 'default_qwen_clip', 'default_qwen_vae', 'default_qwen_edit_clip', 'default_qwen_edit_vae',
            'default_wan_t2v_high_noise_unet', 'default_wan_t2v_low_noise_unet', 'default_wan_i2v_high_noise_unet', 'default_wan_i2v_low_noise_unet',
            'default_wan_low_noise_unet', 'default_wan_clip', 'default_wan_vae', 'default_wan_vision_clip',
            'wan_animation_motion_profile', 'wan_animation_resolution', 'active_model_family', 'default_editing_mode'
        ]
        string_keys_to_strip.extend([
            'flux_ksampler_sampler', 'flux_ksampler_scheduler',
            'sdxl_ksampler_sampler', 'sdxl_ksampler_scheduler',
            'qwen_ksampler_sampler', 'qwen_ksampler_scheduler',
            'qwen_edit_ksampler_sampler', 'qwen_edit_ksampler_scheduler',
            'wan_stage1_add_noise', 'wan_stage1_noise_mode', 'wan_stage1_sampler', 'wan_stage1_scheduler', 'wan_stage1_return_with_leftover_noise',
            'wan_stage2_add_noise', 'wan_stage2_noise_mode', 'wan_stage2_sampler', 'wan_stage2_scheduler', 'wan_stage2_return_with_leftover_noise',
            'flux_upscale_model', 'flux_upscale_sampler', 'flux_upscale_scheduler',
            'sdxl_upscale_model', 'sdxl_upscale_sampler', 'sdxl_upscale_scheduler',
            'qwen_upscale_model', 'qwen_upscale_sampler', 'qwen_upscale_scheduler',
        ])
        display_prompt_key = 'display_prompt_preference'
        allowed_display_prompt_options = ['enhanced', 'original']


        valid_settings = settings.copy()
        defaults = _get_default_settings()

        for key in numeric_keys_float:
            if key in valid_settings:
                try:
                    if valid_settings[key] is None:
                        continue
                    coerced_val = float(valid_settings[key])
                except (ValueError, TypeError):
                    coerced_val = defaults[key]

                bounds = float_bounds.get(key)
                if bounds:
                    min_val, max_val = bounds
                    if coerced_val < min_val:
                        coerced_val = min_val
                    if coerced_val > max_val:
                        coerced_val = max_val

                valid_settings[key] = coerced_val

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
            elif key in valid_settings and valid_settings[key] is None and key not in [
                'selected_model', 'selected_t5_clip', 'selected_clip_l',
                'flux_upscale_model', 'sdxl_upscale_model', 'qwen_upscale_model',
                'selected_vae', 'selected_kontext_model'
            ]: # Allow None for model selections
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

        allowed_motion_profiles = {'slowmo', 'low', 'medium', 'high'}
        motion_profile_val = str(valid_settings.get('wan_animation_motion_profile', defaults['wan_animation_motion_profile'])).lower()
        if motion_profile_val not in allowed_motion_profiles:
            valid_settings['wan_animation_motion_profile'] = defaults['wan_animation_motion_profile']
        else:
            valid_settings['wan_animation_motion_profile'] = motion_profile_val

        resolution_value = str(valid_settings.get('wan_animation_resolution', defaults['wan_animation_resolution'])).lower()
        try:
            width_str, height_str = resolution_value.split('x', 1)
            width_val = int(width_str)
            height_val = int(height_str)
            if width_val <= 0 or height_val <= 0:
                raise ValueError
            valid_settings['wan_animation_resolution'] = f"{width_val}x{height_val}"
        except (ValueError, AttributeError):
            valid_settings['wan_animation_resolution'] = defaults['wan_animation_resolution']

        try:
            duration_val = int(valid_settings.get('wan_animation_duration', defaults['wan_animation_duration']))
        except (ValueError, TypeError):
            duration_val = defaults['wan_animation_duration']
        duration_val = max(8, min(240, duration_val))
        valid_settings['wan_animation_duration'] = duration_val

        allowed_families = set(GENERATION_MODEL_FAMILIES)
        active_family_val = str(valid_settings.get('active_model_family', defaults['active_model_family'])).lower()
        if active_family_val not in allowed_families:
            valid_settings['active_model_family'] = defaults['active_model_family']
        else:
            valid_settings['active_model_family'] = active_family_val

        edit_mode_raw = str(valid_settings.get('default_editing_mode', defaults['default_editing_mode']) or defaults['default_editing_mode']).lower()
        qwen_edit_aliases = {'qwen_edit', 'qwen', 'qwen-image-edit', 'qwen_image_edit', 'qwenedit'}
        kontext_aliases = {'kontext', 'kontext_edit', 'kontext-edit'}
        if edit_mode_raw in qwen_edit_aliases:
            normalized_edit_mode = 'qwen_edit'
        elif edit_mode_raw in kontext_aliases:
            normalized_edit_mode = 'kontext'
        else:
            normalized_edit_mode = defaults['default_editing_mode']
        valid_settings['default_editing_mode'] = normalized_edit_mode


        for key in defaults:
            if key not in valid_settings:
                print(f"Warning: Key '{key}' missing before saving. Adding default.")
                valid_settings[key] = defaults[key]

        sync_active_model_selection(valid_settings)

        with open(settings_file, 'w') as f:
            json.dump(valid_settings, f, indent=2)
    except OSError as e: print(f"Error writing {settings_file}: {e}")
    except TypeError as e: print(f"Type error while saving settings: {e}")
    except Exception as e: print(f"Unexpected error saving settings: {e}"); traceback.print_exc()


def get_model_choices(settings):
    choices: List[discord.SelectOption] = []
    catalogs: Dict[str, Dict[str, set[str]]] = {}

    for model_type in MODEL_SELECTION_PREFIX:
        favorites, items = _load_model_catalog(MODEL_CATALOG_FILES.get(model_type, ""))
        catalogs[model_type] = {
            "favorites": {f for f in favorites},
            "items": {i for i in items},
        }

    current_model_setting = settings.get('selected_model')
    current_model_value = current_model_setting.strip() if isinstance(current_model_setting, str) else None

    canonical_options: List[Dict[str, str]] = []
    seen_values: set[str] = set()

    for model_type in ("flux", "sdxl", "qwen", "qwen_edit", "wan"):
        if model_type not in MODEL_SELECTION_PREFIX:
            continue
        prefix_label = MODEL_SELECTION_PREFIX[model_type]
        display_tag = prefix_label.upper()
        favorites_sorted = sorted(catalogs[model_type]["favorites"], key=str.lower)
        items_sorted = sorted(catalogs[model_type]["items"], key=str.lower)

        for model in favorites_sorted:
            value = f"{prefix_label}: {model}"
            if value not in seen_values:
                canonical_options.append({
                    'label': f"⭐ [{display_tag}] {model}",
                    'value': value,
                })
                seen_values.add(value)

        for model in items_sorted:
            value = f"{prefix_label}: {model}"
            if value not in seen_values:
                canonical_options.append({
                    'label': f"[{display_tag}] {model}",
                    'value': value,
                })
                seen_values.add(value)

    if current_model_value and current_model_value not in seen_values:
        current_type, actual_name = resolve_model_type_from_prefix(current_model_value)
        display_prefix = MODEL_SELECTION_PREFIX.get(current_type, current_model_value.split(":", 1)[0].strip() if ":" in current_model_value else current_type or "?")
        display_tag = display_prefix.upper()
        favorites_for_type = catalogs.get(current_type, {}).get("favorites", set())
        actual_display_name = actual_name or (current_model_value.split(":", 1)[-1].strip() if ":" in current_model_value else current_model_value)
        is_favorite = bool(actual_display_name and actual_display_name in favorites_for_type)
        label_prefix = "⭐ " if is_favorite else ""
        canonical_options.insert(0, {
            'label': f"{label_prefix}[{display_tag}] {actual_display_name}",
            'value': current_model_value,
        })
        seen_values.add(current_model_value)

    for option_data in canonical_options:
        is_default = (current_model_value is not None and option_data['value'] == current_model_value)
        choices.append(
            discord.SelectOption(
                label=option_data['label'][:100],
                value=option_data['value'],
                default=is_default,
            )
        )

    if choices and not any(o.default for o in choices):
        choices[0].default = True

    return choices[:20]


def _build_model_choice_options(settings, model_type: str, setting_key: str) -> List[discord.SelectOption]:
    """Return select options for a specific model catalog."""

    favorites, items = _load_model_catalog(MODEL_CATALOG_FILES.get(model_type, ""))

    current_value = settings.get(setting_key)
    if isinstance(current_value, str):
        current_value = current_value.strip()
    else:
        current_value = None

    if setting_key == WAN_T2V_HIGH_NOISE_KEY and not current_value:
        alias_value = settings.get(WAN_CHECKPOINT_KEY)
        if isinstance(alias_value, str) and alias_value.strip():
            current_value = alias_value.strip()
            settings[setting_key] = current_value

    display_tag = MODEL_SELECTION_PREFIX.get(model_type, model_type.upper())
    canonical_options: List[Dict[str, str]] = []
    seen: set[str] = set()

    for model in sorted(favorites, key=str.lower):
        value = model
        if value not in seen:
            canonical_options.append({
                "label": f"⭐ [{display_tag.upper()}] {model}",
                "value": value,
            })
            seen.add(value)

    for model in sorted(items, key=str.lower):
        value = model
        if value not in seen:
            canonical_options.append({
                "label": f"[{display_tag.upper()}] {model}",
                "value": value,
            })
            seen.add(value)

    if current_value and current_value not in seen:
        canonical_options.insert(0, {
            "label": f"[{display_tag.upper()}] {current_value}",
            "value": current_value,
        })

    select_options: List[discord.SelectOption] = []
    for option in canonical_options:
        select_options.append(
            discord.SelectOption(
                label=option["label"][:100],
                value=option["value"],
                default=current_value is not None and option["value"] == current_value,
            )
        )

    if select_options and not any(option.default for option in select_options):
        select_options[0].default = True

    return select_options[:20]


def get_default_flux_model_choices(settings):
    return _build_model_choice_options(settings, "flux", "default_flux_model")


def get_default_sdxl_model_choices(settings):
    return _build_model_choice_options(settings, "sdxl", "default_sdxl_checkpoint")


def get_default_qwen_model_choices(settings):
    return _build_model_choice_options(settings, "qwen", "default_qwen_checkpoint")


def get_default_qwen_edit_model_choices(settings):
    return _build_model_choice_options(settings, "qwen_edit", "default_qwen_edit_checkpoint")


def get_default_wan_model_choices(settings):
    return _build_model_choice_options(settings, "wan", WAN_T2V_HIGH_NOISE_KEY)


def get_active_model_family_choices(settings):
    current_family = str(settings.get('active_model_family', 'flux') or 'flux').lower()
    options: List[discord.SelectOption] = []
    fallback_key_map = {
        'flux': 'default_flux_model',
        'sdxl': 'default_sdxl_checkpoint',
        'qwen': 'default_qwen_checkpoint',
        'qwen_edit': 'default_qwen_edit_checkpoint',
        'wan': WAN_T2V_HIGH_NOISE_KEY,
    }
    for family_key in GENERATION_MODEL_FAMILIES:
        prefix_label = MODEL_SELECTION_PREFIX.get(family_key, family_key)
        default_model_name = settings.get(fallback_key_map.get(family_key, ''), None)
        if isinstance(default_model_name, str) and default_model_name.strip():
            display_name = f"[{prefix_label.upper()}] {default_model_name.strip()}"
        else:
            display_name = f"[{prefix_label.upper()}] (No default set)"
        options.append(
            discord.SelectOption(
                label=display_name[:100],
                value=family_key,
                default=(family_key == current_family),
            )
        )
    if options and not any(opt.default for opt in options):
        options[0].default = True
    return options[:20]


def get_wan_animation_resolution_choices(settings):
    current_value = str(settings.get('wan_animation_resolution', '512x512') or '512x512').lower()
    preset_resolutions = [
        '512x512', '768x768', '960x540', '1024x576', '1024x1024', '1280x720', '1536x864', '1920x1080'
    ]
    if current_value not in preset_resolutions:
        preset_resolutions.append(current_value)
    options: List[discord.SelectOption] = []
    for res in preset_resolutions:
        label = f"Resolution: {res}"
        options.append(
            discord.SelectOption(
                label=label[:100],
                value=res,
                default=(res == current_value),
            )
        )
    if options and not any(opt.default for opt in options):
        options[0].default = True
    return options[:20]


def get_wan_animation_duration_choices(settings):
    try:
        current_duration = int(settings.get('wan_animation_duration', 33))
    except (TypeError, ValueError):
        current_duration = 33
    preset_durations = [16, 24, 33, 48, 60, 90, 120, 180, 240]
    if current_duration not in preset_durations:
        preset_durations.append(current_duration)
    preset_durations = sorted({max(8, min(240, d)) for d in preset_durations})
    options: List[discord.SelectOption] = []
    for duration in preset_durations:
        label = f"Frames: {duration}"
        options.append(
            discord.SelectOption(
                label=label[:100],
                value=str(duration),
                default=(duration == current_duration),
            )
        )
    if options and not any(opt.default for opt in options):
        options[0].default = True
    return options[:20]


def get_wan_animation_motion_profile_choices(settings):
    current_profile = str(settings.get('wan_animation_motion_profile', 'medium') or 'medium').lower()
    options: List[discord.SelectOption] = []
    for profile in ['slowmo', 'low', 'medium', 'high']:
        label = f"Motion: {profile.capitalize()}"
        options.append(
            discord.SelectOption(
                label=label[:100],
                value=profile,
                default=(profile == current_profile),
            )
        )
    if options and not any(opt.default for opt in options):
        options[0].default = True
    return options[:20]


def _build_enum_choice_options(
    settings: dict,
    setting_key: str,
    options: List[str],
    label_prefix: str,
) -> List[discord.SelectOption]:
    fallback = options[0] if options else ""
    current_value_raw = settings.get(setting_key, fallback)
    current_value = str(current_value_raw or fallback).strip() or fallback

    ordered: List[str] = []
    if current_value:
        ordered.append(current_value)
    for option in options:
        if option not in ordered:
            ordered.append(option)

    ordered = ordered[:25]
    choices: List[discord.SelectOption] = []
    for option in ordered:
        label = f"{label_prefix}: {option}"
        choices.append(
            discord.SelectOption(
                label=label[:100],
                value=option,
                default=(option == current_value),
            )
        )

    if choices and not any(choice.default for choice in choices):
        choices[0].default = True

    return choices


def get_qwen_ksampler_sampler_choices(settings):
    return _build_enum_choice_options(settings, 'qwen_ksampler_sampler', KSAMPLER_SAMPLER_OPTIONS, 'Sampler (Qwen)')


def get_qwen_ksampler_scheduler_choices(settings):
    return _build_enum_choice_options(settings, 'qwen_ksampler_scheduler', KSAMPLER_SCHEDULER_OPTIONS, 'Scheduler (Qwen)')


def get_qwen_edit_ksampler_sampler_choices(settings):
    return _build_enum_choice_options(settings, 'qwen_edit_ksampler_sampler', KSAMPLER_SAMPLER_OPTIONS, 'Sampler (Qwen Edit)')


def get_qwen_edit_ksampler_scheduler_choices(settings):
    return _build_enum_choice_options(settings, 'qwen_edit_ksampler_scheduler', KSAMPLER_SCHEDULER_OPTIONS, 'Scheduler (Qwen Edit)')


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

    return choices[:20]


def get_t5_clip_choices(settings): return get_clip_choices(settings, 't5', 'selected_t5_clip')
def get_clip_l_choices(settings): return get_clip_choices(settings, 'clip_L', 'selected_clip_l')
def get_sdxl_clip_choices(settings): return get_clip_choices(settings, 'clip_L', 'default_sdxl_clip')
def get_qwen_clip_choices(settings): return get_clip_choices(settings, 'qwen', 'default_qwen_clip')
def get_qwen_edit_clip_choices(settings): return get_clip_choices(settings, 'qwen', 'default_qwen_edit_clip')
def get_wan_clip_choices(settings): return get_clip_choices(settings, 'wan', 'default_wan_clip')
def get_wan_vision_clip_choices(settings): return get_clip_choices(settings, 'vision', 'default_wan_vision_clip')


def get_style_choices_for_model(settings, model_type: str):
    styles = load_styles_config()
    spec = get_model_spec(model_type)
    current_style = str(settings.get(spec.defaults.style_key, 'off') or 'off').strip()

    allowed_tags = STYLE_FILTERS.get(model_type, {"all"})
    filtered_styles = {
        name: data
        for name, data in styles.items()
        if isinstance(data, dict) and data.get('model_type', 'all') in allowed_tags
    }

    canonical_options: List[dict] = []
    favorite_styles: List[dict] = []
    other_styles: List[dict] = []
    off_option: Optional[dict] = None

    for style_raw, data_raw in filtered_styles.items():
        style_name = style_raw.strip()
        is_favorite = bool(data_raw.get('favorite'))
        label_prefix = "⭐" if is_favorite and style_name != "off" else ("🔴" if style_name == "off" else "")
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

    choices: List[discord.SelectOption] = []
    for option_data in canonical_options:
        is_default = (option_data['value'] == current_style)
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

    return choices[:20]


def get_style_choices_flux(settings):
    return get_style_choices_for_model(settings, "flux")


def get_style_choices_sdxl(settings):
    return get_style_choices_for_model(settings, "sdxl")


def get_style_choices_qwen(settings):
    return get_style_choices_for_model(settings, "qwen")


def get_style_choices_wan(settings):
    return get_style_choices_for_model(settings, "wan")


def get_steps_choices_for_model(settings, model_type: str):
    spec = get_model_spec(model_type)
    try:
        current_steps = int(settings.get(spec.defaults.steps_key, spec.defaults.steps_fallback))
    except (ValueError, TypeError):
        current_steps = spec.defaults.steps_fallback

    base_options = DEFAULT_STEP_OPTIONS.get(model_type, DEFAULT_STEP_OPTIONS['flux'])
    steps_options = sorted(set(base_options + [current_steps]))
    label = f"Steps ({get_model_spec(model_type).label})"

    choices = [
        discord.SelectOption(label=f"{step} {label}", value=str(step), default=(step == current_steps))
        for step in steps_options
    ]
    if choices and not any(option.default for option in choices):
        choices[0].default = True
    return choices[:20]


def get_steps_choices(settings):
    return get_steps_choices_for_model(settings, "flux")


def get_sdxl_steps_choices(settings):
    return get_steps_choices_for_model(settings, "sdxl")


def get_qwen_steps_choices(settings):
    return get_steps_choices_for_model(settings, "qwen")


def get_qwen_edit_steps_choices(settings):
    try:
        current_steps = int(float(settings.get('qwen_edit_steps', 28)))
    except (ValueError, TypeError):
        current_steps = 28

    base_options = DEFAULT_STEP_OPTIONS.get('qwen_edit', DEFAULT_STEP_OPTIONS['qwen'])
    steps_options = sorted({int(step) for step in base_options + [current_steps]})
    label = "Steps (Qwen Edit)"

    choices: List[discord.SelectOption] = []
    for step in steps_options:
        choices.append(
            discord.SelectOption(
                label=f"{step} {label}",
                value=str(step),
                default=(step == current_steps),
            )
        )

    if choices and not any(option.default for option in choices):
        choices[0].default = True

    return choices[:20]


def get_wan_steps_choices(settings):
    return get_steps_choices_for_model(settings, "wan")


def get_guidance_choices_for_model(settings, model_type: str):
    spec = get_model_spec(model_type)
    try:
        current_guidance = float(settings.get(spec.defaults.guidance_key, spec.defaults.guidance_fallback))
    except (ValueError, TypeError):
        current_guidance = spec.defaults.guidance_fallback

    config = GUIDANCE_CONFIG.get(model_type, GUIDANCE_CONFIG['flux'])
    values = [f"{g:.1f}" for g in np.arange(config['start'], config['stop'] + config['step'], config['step'])]
    current_str = f"{current_guidance:.1f}"
    if current_str not in values:
        values.append(current_str)
        values.sort(key=float)

    label_prefix = f"Guidance ({get_model_spec(model_type).label})"
    choices = [
        discord.SelectOption(
            label=f"{label_prefix}: {value}",
            value=value,
            default=(abs(float(value) - current_guidance) < 0.01),
        )
        for value in values
    ]
    if choices and not any(option.default for option in choices):
        choices[0].default = True
    return choices[:20]


def get_guidance_choices(settings):
    return get_guidance_choices_for_model(settings, "flux")


def get_sdxl_guidance_choices(settings):
    return get_guidance_choices_for_model(settings, "sdxl")


def get_qwen_guidance_choices(settings):
    return get_guidance_choices_for_model(settings, "qwen")


def get_qwen_edit_guidance_choices(settings):
    try:
        current_guidance = float(settings.get('default_guidance_qwen_edit', 2.5))
    except (ValueError, TypeError):
        current_guidance = 2.5

    config = GUIDANCE_CONFIG.get('qwen_edit', GUIDANCE_CONFIG['qwen'])
    values = [round(value, 1) for value in np.arange(config['start'], config['stop'] + config['step'], config['step'])]
    if round(current_guidance, 1) not in values:
        values.append(round(current_guidance, 1))
        values = sorted(set(values))

    label_prefix = "Guidance (Qwen Edit)"
    choices: List[discord.SelectOption] = []
    for value in values:
        value = float(value)
        value_str = f"{value:.1f}"
        choices.append(
            discord.SelectOption(
                label=f"{label_prefix}: {value_str}",
                value=value_str,
                default=bool(abs(value - current_guidance) < 0.05),
            )
        )

    if choices and not any(option.default for option in choices):
        choices[0].default = True

    return choices[:20]


def get_wan_guidance_choices(settings):
    return get_guidance_choices_for_model(settings, "wan")


def get_qwen_edit_shift_choices(settings):
    try:
        current_shift = float(settings.get('qwen_edit_shift', 0.0))
    except (ValueError, TypeError):
        current_shift = 0.0

    base_values = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    rounded_current = round(current_shift, 2)
    rounded_set = {round(v, 2) for v in base_values}
    if rounded_current not in rounded_set:
        rounded_set.add(rounded_current)
    ordered_values = sorted(rounded_set)

    choices: List[discord.SelectOption] = []
    for value in ordered_values:
        value = float(value)
        if value.is_integer():
            display = f"{int(value)}"
        else:
            display = f"{value:.2f}".rstrip('0').rstrip('.')
        choices.append(
            discord.SelectOption(
                label=f"Shift: {display}",
                value=str(value),
                default=bool(abs(value - current_shift) < 0.05),
            )
        )

    if choices and not any(option.default for option in choices):
        choices[0].default = True

    return choices[:20]


def get_qwen_edit_denoise_choices(settings):
    try:
        current_denoise = float(settings.get('qwen_edit_denoise', 0.6))
    except (ValueError, TypeError):
        current_denoise = 0.6

    base_values = [round(step, 2) for step in np.linspace(0.0, 1.0, 11)]
    if round(current_denoise, 2) not in base_values:
        base_values.append(round(current_denoise, 2))
        base_values = sorted({round(v, 2) for v in base_values})

    choices: List[discord.SelectOption] = []
    for value in base_values:
        value = float(value)
        display = f"{value:.2f}".rstrip('0').rstrip('.') if value not in (0.0, 1.0) else f"{value:.1f}"
        choices.append(
            discord.SelectOption(
                label=f"Denoise: {display}",
                value=f"{value:.2f}",
                default=bool(abs(value - current_denoise) < 0.05),
            )
        )

    if choices and not any(option.default for option in choices):
        choices[0].default = True

    return choices[:20]


def get_qwen_edit_cfg_rescale_choices(settings):
    try:
        current_rescale = float(settings.get('qwen_edit_cfg_rescale', 1.0))
    except (ValueError, TypeError):
        current_rescale = 1.0

    base_values = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
    rounded_current = round(current_rescale, 2)
    rounded_values = {round(value, 2) for value in base_values}
    rounded_values.add(rounded_current)
    ordered_values = sorted(rounded_values)

    choices: List[discord.SelectOption] = []
    for value in ordered_values:
        value_str = f"{value:.2f}"
        choices.append(
            discord.SelectOption(
                label=f"CFG Rescale: {value_str}",
                value=value_str,
                default=bool(abs(value - rounded_current) < 0.01),
            )
        )

    if choices and not any(option.default for option in choices):
        choices[0].default = True

    return choices[:20]


def get_wan_t2v_high_unet_choices(settings):
    return _build_model_choice_options(settings, "wan", WAN_T2V_HIGH_NOISE_KEY)


def get_wan_t2v_low_unet_choices(settings):
    return _build_model_choice_options(settings, "wan", WAN_T2V_LOW_NOISE_KEY)


def get_wan_i2v_high_unet_choices(settings):
    return _build_model_choice_options(settings, "wan", WAN_I2V_HIGH_NOISE_KEY)


def get_wan_i2v_low_unet_choices(settings):
    return _build_model_choice_options(settings, "wan", WAN_I2V_LOW_NOISE_KEY)


def get_wan_low_noise_unet_choices(settings):
    return get_wan_t2v_low_unet_choices(settings)

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
    return choices[:20]

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
    return options[:20]

def get_llm_model_choices(settings, provider=None):
    if provider is None: provider = settings.get('llm_provider', 'gemini')
    provider_data = llm_models_config.get('providers', {}).get(provider, {})
    models_raw = provider_data.get('models', [])
    models = [m.strip() for m in models_raw if isinstance(m, str)]
    favorites_raw = provider_data.get('favorites', [])
    favorites = [m.strip() for m in favorites_raw if isinstance(m, str)]
    if not models:
        provider_display = provider_data.get("display_name", provider.capitalize())
        return [discord.SelectOption(label=f"No models for {provider_display}", value="none", default=True)]
    current_model_key = f"llm_model_{provider}"; current_model_setting = settings.get(current_model_key)
    current_model = current_model_setting.strip() if isinstance(current_model_setting, str) else None

    canonical_options = []
    seen_values = set()

    for model in sorted({m for m in favorites if m in models}, key=str.lower):
        if model not in seen_values:
            canonical_options.append({'label': f"⭐ {model}", 'value': model})
            seen_values.add(model)

    for model in sorted(models, key=str.lower):
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

    return choices[:20]

def get_mp_size_choices(settings):
    try:
        current_size_float = float(settings.get('default_mp_size', 1.0))
    except (ValueError, TypeError):
        current_size_float = 1.0

    allowed_sizes = ["0.25", "0.5", "1.0", "1.25", "1.5", "1.75", "2.0", "2.5", "3.0", "4.0"]
    current_size_str = f"{current_size_float:.2f}".rstrip('0').rstrip('.')
    if f"{current_size_str}.0" in allowed_sizes:
        current_size_str += ".0"
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

    return choices[:20]

def get_upscale_model_choices(settings, setting_key: str):
    choices = []; models_data = {}; # Changed var name to avoid conflict
    try:
        from comfyui_api import get_available_comfyui_models
        models_data = get_available_comfyui_models(suppress_summary_print=True)
    except Exception: pass
    upscale_models_raw = []
    if isinstance(models_data, dict):
        upscale_models_raw.extend(models_data.get('upscaler', []))
        if not upscale_models_raw: upscale_models_raw.extend(models_data.get('unet', [])) # Fallback
    # Include locally available models from the configured directory as a
    # fallback in case the ComfyUI API does not report any upscalers.
    try:
        with open('config.json', 'r') as cfg_file:
            cfg_data = json.load(cfg_file)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        cfg_data = {}

    local_upscale_models = set()
    upscale_root = None
    if isinstance(cfg_data, dict):
        upscale_root = cfg_data.get('MODELS', {}).get('UPSCALE_MODELS') if isinstance(cfg_data.get('MODELS', {}), dict) else None

    if isinstance(upscale_root, str) and upscale_root.strip():
        normalized_root = os.path.abspath(upscale_root.strip())
        if os.path.isdir(normalized_root):
            try:
                allowed_exts = {'.pth', '.pt', '.onnx', '.safetensors', '.ckpt', '.bin'}
                for entry in os.listdir(normalized_root):
                    base = entry.strip()
                    if not base:
                        continue
                    _, ext = os.path.splitext(base)
                    if ext.lower() in allowed_exts:
                        local_upscale_models.add(base)
            except OSError as os_error:
                print(f"SettingsManager: Unable to scan upscale model directory '{normalized_root}': {os_error}")

    if local_upscale_models:
        upscale_models_raw.extend(sorted(local_upscale_models))

    upscale_models = sorted(list(set(u.strip() for u in upscale_models_raw if isinstance(u, str) and u.strip())))
    current_upscale_model_setting = settings.get(setting_key)
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
    return choices[:20]


def _build_vae_choices(settings, setting_key: str):
    choices = []
    models_data = {}
    try:
        from comfyui_api import get_available_comfyui_models
        models_data = get_available_comfyui_models(suppress_summary_print=True)
    except Exception:
        models_data = {}

    vae_models_raw = models_data.get('vae', []) if isinstance(models_data, dict) else []
    vae_models = sorted(list({v.strip() for v in vae_models_raw if isinstance(v, str)}))
    current_setting = settings.get(setting_key)
    current_value = current_setting.strip() if isinstance(current_setting, str) else None

    canonical_options = []
    seen_values = set()
    for vae in vae_models:
        if vae not in seen_values:
            canonical_options.append({'label': vae, 'value': vae})
            seen_values.add(vae)

    if current_value and current_value not in seen_values:
        label = f"{current_value} (Custom?)"
        canonical_options.insert(0, {'label': label, 'value': current_value})

    for option_data in canonical_options:
        is_default = (option_data['value'] == current_value)
        choices.append(
            discord.SelectOption(
                label=option_data['label'][:100],
                value=option_data['value'],
                default=is_default,
            )
        )

    if not choices:
        choices.append(
            discord.SelectOption(
                label="None Available/Selected",
                value="None",
                default=True if not current_value else False,
            )
        )
    elif choices and not any(c.default for c in choices):
        choices[0].default = True

    return choices[:20]


def get_vae_choices(settings):
    return _build_vae_choices(settings, 'selected_vae')


def get_qwen_vae_choices(settings):
    return _build_vae_choices(settings, 'default_qwen_vae')


def get_qwen_edit_vae_choices(settings):
    return _build_vae_choices(settings, 'default_qwen_edit_vae')


def get_wan_vae_choices(settings):
    return _build_vae_choices(settings, 'default_wan_vae')


def get_flux_vae_choices(settings):
    return _build_vae_choices(settings, 'default_flux_vae')


def get_sdxl_vae_choices(settings):
    return _build_vae_choices(settings, 'default_sdxl_vae')

def get_display_prompt_preference_choices(settings):
    current_preference = settings.get('display_prompt_preference', 'enhanced')
    return [discord.SelectOption(label="Show Enhanced Prompt ✨", value="enhanced", default=(current_preference == 'enhanced')), discord.SelectOption(label="Show Original Prompt ✍️", value="original", default=(current_preference == 'original'))]


def get_editing_mode_choices(settings):
    current_mode = str(settings.get('default_editing_mode', 'kontext') or 'kontext').lower()
    options = [
        ("Kontext Editing", 'kontext'),
        ("Qwen Edit", 'qwen_edit'),
    ]
    return [
        discord.SelectOption(label=label, value=value, default=(value == current_mode))
        for label, value in options
    ]

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

    return choices[:20]


def resolve_model_for_type(settings: Dict[str, object], desired_type: str) -> Optional[str]:
    desired_key = (desired_type or "").lower()
    if desired_key not in MODEL_SELECTION_PREFIX:
        return None

    selected_model_setting = settings.get('selected_model')
    selected_model_value = selected_model_setting.strip() if isinstance(selected_model_setting, str) else None
    if selected_model_value:
        selected_type, _ = resolve_model_type_from_prefix(selected_model_value)
        if selected_type == desired_key:
            return selected_model_value

    fallback_key_map = {
        'flux': 'default_flux_model',
        'sdxl': 'default_sdxl_checkpoint',
        'qwen': 'default_qwen_checkpoint',
        'qwen_edit': 'default_qwen_edit_checkpoint',
        'wan': WAN_T2V_HIGH_NOISE_KEY,
    }

    fallback_model = None
    fallback_setting_key = fallback_key_map.get(desired_key)
    if fallback_setting_key:
        fallback_setting_value = settings.get(fallback_setting_key)
        if isinstance(fallback_setting_value, str) and fallback_setting_value.strip():
            fallback_model = fallback_setting_value.strip()

    if not fallback_model and desired_key == 'qwen_edit':
        legacy_setting = settings.get('default_qwen_checkpoint')
        if isinstance(legacy_setting, str) and legacy_setting.strip():
            fallback_model = legacy_setting.strip()

    if not fallback_model:
        fallback_model = _get_first_model_from_catalog(desired_key)

    if not fallback_model:
        return None

    prefix_label = MODEL_SELECTION_PREFIX[desired_key]
    return f"{prefix_label}: {fallback_model}"


# --- END OF FILE settings_manager.py ---
