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

    default_model_setting = None
    if default_flux_model_raw: default_model_setting = f"Flux: {default_flux_model_raw}"
    elif default_sdxl_checkpoint_raw: default_model_setting = f"SDXL: {default_sdxl_checkpoint_raw}"

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
        "selected_kontext_model": default_flux_model_raw,
        "steps": 32,
        "sdxl_steps": 26,
        "selected_t5_clip": default_t5,
        "selected_clip_l": default_l,
        "selected_upscale_model": None,
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

    for model in sorted(flux_favorites):
        value = f"Flux: {model}"
        if value not in seen_values:
            canonical_options.append({'label': f"⭐ [FLUX] {model}", 'value': value})
            seen_values.add(value)
    for model in sorted(sdxl_favorites):
        value = f"SDXL: {model}"
        if value not in seen_values:
            canonical_options.append({'label': f"⭐ [SDXL] {model}", 'value': value})
            seen_values.add(value)

    all_flux_models_raw = []
    for model_type_key in ['safetensors', 'sft', 'gguf']:
        all_flux_models_raw.extend(flux_models_data.get(model_type_key, []))

    for model_raw in sorted(list(set(m.strip() for m in all_flux_models_raw if isinstance(m, str)))):
        value = f"Flux: {model_raw}"
        if value not in seen_values:
            canonical_options.append({'label': f"[FLUX] {model_raw}", 'value': value})
            seen_values.add(value)

    all_sdxl_checkpoints_raw = []
    if isinstance(sdxl_checkpoints_data.get('checkpoints'), list): all_sdxl_checkpoints_raw = sdxl_checkpoints_data['checkpoints']
    else:
        for key, value in sdxl_checkpoints_data.items():
            if isinstance(value, list) and key != 'favorites': all_sdxl_checkpoints_raw.extend(value)
    
    for model_raw in sorted(list(set(c for c in all_sdxl_checkpoints_raw if isinstance(c, str)))):
        value = f"SDXL: {model_raw.strip()}"
        if value not in seen_values:
            canonical_options.append({'label': f"[SDXL] {model_raw.strip()}", 'value': value})
            seen_values.add(value)
    
    if current_model_setting and current_model_setting not in seen_values:
        model_type, actual_name = (current_model_setting.split(":",1)[0].strip().lower(), current_model_setting.split(":",1)[1].strip()) if ":" in current_model_setting else (None, current_model_setting)
        is_fav = (model_type == "flux" and actual_name in flux_favorites) or \
                 (model_type == "sdxl" and actual_name in sdxl_favorites)
        label = f"{'⭐ ' if is_fav else ''}[{model_type.upper() if model_type else '??'}] {actual_name}"
        canonical_options.insert(0, {'label': label, 'value': current_model_setting})

    for option_data in canonical_options:
        is_default = (option_data['value'] == current_model_setting)
        choices.append(discord.SelectOption(label=option_data['label'][:100], value=option_data['value'], default=is_default))

    if choices and not any(o.default for o in choices):
        if choices: choices[0].default = True

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
