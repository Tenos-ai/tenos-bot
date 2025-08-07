# --- START OF FILE settings_manager.py ---
# START OF FILE settings_manager.py

import json
import discord
import os
import numpy as np
import traceback
import copy
import threading

_settings_cache = None
_settings_mtime = None
_settings_lock = threading.RLock()

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
@@ -62,63 +68,79 @@ def load_styles_config():
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
    global _settings_cache, _settings_mtime

    try:
        current_mtime = os.path.getmtime(settings_file)
    except OSError:
        current_mtime = None

    with _settings_lock:
        if _settings_cache is not None and _settings_mtime == current_mtime:
            return copy.deepcopy(_settings_cache)

    try:
        if not os.path.exists(settings_file):
            print(f"Warning: {settings_file} not found. Creating default settings.")
            settings = _get_default_settings()
            save_settings(settings)
            with _settings_lock:
                return copy.deepcopy(_settings_cache)

        with open(settings_file, 'r') as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error parsing {settings_file} (invalid JSON): {e}. Returning defaults.")
                settings = _get_default_settings()
                with _settings_lock:
                    _settings_cache = copy.deepcopy(settings)
                    _settings_mtime = current_mtime
                    return copy.deepcopy(_settings_cache)
        
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

@@ -345,52 +367,57 @@ def load_settings():
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


        if updated:
             print(f"Updating {settings_file} with defaults/corrections.")
             save_settings(settings)
        with _settings_lock:
            _settings_cache = copy.deepcopy(settings)
            try:
                _settings_mtime = os.path.getmtime(settings_file)
            except OSError:
                _settings_mtime = None
            return copy.deepcopy(_settings_cache)
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
    try:
        if os.path.exists('checkpointslist.json'):
            with open('checkpointslist.json', 'r') as f: checkpoints = json.load(f)
            if isinstance(checkpoints, dict) and isinstance(checkpoints.get('checkpoints'),list):
                default_sdxl_checkpoint_raw = next((c.strip() for c in checkpoints['checkpoints'] if isinstance(c, str) and c.strip()), None)
            elif isinstance(checkpoints, list):
                 default_sdxl_checkpoint_raw = next((c.strip() for c in checkpoints if isinstance(c, str) and c.strip()), None)
    except Exception: default_sdxl_checkpoint_raw = None
@@ -423,118 +450,133 @@ def _get_default_settings():
        "selected_vae": None,
        "default_style_flux": "off",
        "default_style_sdxl": "off",
        "default_variation_mode": "weak",
        "variation_batch_size": 1,
        "default_batch_size": 1,
        "default_guidance": 3.5,
        "default_guidance_sdxl": 7.0,
        "default_sdxl_negative_prompt": "",
        "default_mp_size": 1.0,
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
    }

def save_settings(settings):
    settings_file = 'settings.json'
    global _settings_cache, _settings_mtime
    try:
        numeric_keys_float = ['default_guidance', 'default_guidance_sdxl', 'upscale_factor', 'default_mp_size', 'kontext_guidance', 'kontext_mp_size']
        numeric_keys_int = ['steps', 'sdxl_steps', 'default_batch_size', 'kontext_steps', 'variation_batch_size']
        bool_keys = ['remix_mode', 'llm_enhancer_enabled']
        string_keys_to_strip = [
            'llm_provider', 'llm_model_gemini', 'llm_model_groq', 'llm_model_openai',
            'selected_model', 'selected_t5_clip', 'selected_clip_l', 'selected_upscale_model',
            'selected_vae', 'default_style_flux', 'default_style_sdxl', 'default_sdxl_negative_prompt',
            'selected_kontext_model'
        ]
        display_prompt_key = 'display_prompt_preference'
        allowed_display_prompt_options = ['enhanced', 'original']


        valid_settings = copy.deepcopy(settings)
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
            elif key in valid_settings and valid_settings[key] is None and key not in ['selected_model', 'selected_t5_clip', 'selected_clip_l', 'selected_upscale_model', 'selected_vae', 'selected_kontext_model']: # Allow None for model selections
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


        for key in defaults:
            if key not in valid_settings:
                print(f"Warning: Key '{key}' missing before saving. Adding default.")
                valid_settings[key] = defaults[key]

        with _settings_lock:
            with open(settings_file, 'w') as f:
                json.dump(valid_settings, f, indent=2)
            _settings_cache = copy.deepcopy(valid_settings)
            try:
                _settings_mtime = os.path.getmtime(settings_file)
            except OSError:
                _settings_mtime = None
    except OSError as e: print(f"Error writing {settings_file}: {e}")
    except TypeError as e: print(f"Type error while saving settings: {e}")
    except Exception as e: print(f"Unexpected error saving settings: {e}"); traceback.print_exc()


def clear_settings_cache():
    """Invalidate the in-memory settings cache."""
    global _settings_cache, _settings_mtime
    with _settings_lock:
        _settings_cache = None
        _settings_mtime = None


def get_model_choices(settings):
    choices = []
    flux_models_data = {}; sdxl_checkpoints_data = {}
    try:
        if os.path.exists('modelslist.json'):
            with open('modelslist.json', 'r') as f: flux_models_data = json.load(f)
        if not isinstance(flux_models_data, dict): flux_models_data = {}
    except Exception: flux_models_data = {}
    try:
        if os.path.exists('checkpointslist.json'):
            with open('checkpointslist.json', 'r') as f: sdxl_checkpoints_data = json.load(f)
        if not isinstance(sdxl_checkpoints_data, dict): sdxl_checkpoints_data = {}
    except Exception: sdxl_checkpoints_data = {}

    current_model_setting = settings.get('selected_model')
    if isinstance(current_model_setting, str): current_model_setting = current_model_setting.strip()

    flux_favorites_raw = flux_models_data.get('favorites', [])
    flux_favorites = [f.strip() for f in flux_favorites_raw if isinstance(f, str)]
    sdxl_favorites_raw = sdxl_checkpoints_data.get('favorites', [])
    sdxl_favorites = [f.strip() for f in sdxl_favorites_raw if isinstance(f, str)]
    
    canonical_options = []
    seen_values = set()

