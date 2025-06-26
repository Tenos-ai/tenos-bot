# START OF FILE settings_manager.py

import json
import discord
import os
import numpy as np
import traceback

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
            return default_config
        with open('llm_models.json', 'r') as f:
            config = json.load(f)
        if not isinstance(config, dict) or "providers" not in config or not isinstance(config["providers"], dict):
            print("SettingsManager Error: llm_models.json has invalid structure. Using default.")
            return default_config
        
        if "openai" not in config["providers"]:
            print("SettingsManager: Adding default OpenAI provider to llm_models.json")
            config["providers"]["openai"] = default_config["providers"]["openai"]
            # try:
            #     with open('llm_models.json', 'w') as f_write:
            #         json.dump(config, f_write, indent=2)
            # except Exception as e_write:
            #     print(f"SettingsManager Error: Could not save updated llm_models.json: {e_write}")

        for key, data in config["providers"].items():
            if not isinstance(data, dict) or "display_name" not in data or "models" not in data or not isinstance(data["models"], list):
                print(f"SettingsManager Warning: Invalid structure for provider '{key}'. Reverting to default for this provider.")
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

        default_settings = _get_default_settings()
        updated = False
        for key, default_value in default_settings.items():
            if key not in settings:
                print(f"Warning: Setting '{key}' missing. Adding default value: {default_value}")
                settings[key] = default_value
                updated = True

        numeric_keys_float = ['default_guidance', 'default_guidance_sdxl', 'upscale_factor']
        numeric_keys_int = ['steps', 'default_batch_size']
        bool_keys = ['remix_mode', 'llm_enhancer_enabled']
        mp_size_key = 'default_mp_size'
        allowed_mp_sizes = ["0.25", "0.5", "1", "1.25", "1.5", "1.75", "2", "2.5", "3", "4"]
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

        if mp_size_key in settings:
            current_mp_value = str(settings[mp_size_key])
            if current_mp_value not in allowed_mp_sizes:
                print(f"Warning: Setting '{mp_size_key}' has invalid value '{current_mp_value}'. Resetting to default.")
                settings[mp_size_key] = default_settings[mp_size_key]
                updated = True
            else:
                settings[mp_size_key] = current_mp_value
        else:
            pass

        if display_prompt_key in settings:
            current_display_pref = str(settings[display_prompt_key]).lower()
            if current_display_pref not in allowed_display_prompt_options:
                print(f"Warning: Setting '{display_prompt_key}' has invalid value '{current_display_pref}'. Resetting to default.")
                settings[display_prompt_key] = default_settings[display_prompt_key]
                updated = True
            else:
                settings[display_prompt_key] = current_display_pref
        else:
             pass


        llm_string_keys = ['llm_provider', 'llm_model_gemini', 'llm_model_groq', 'llm_model_openai']
        for key in llm_string_keys:
            if key in settings:
                if settings[key] is None or isinstance(settings[key], str):
                    if isinstance(settings[key], str):
                        stripped_val = settings[key].strip()
                        if settings[key] != stripped_val: updated = True
                        settings[key] = stripped_val
                    continue
                else:
                    print(f"Warning: Setting '{key}' has invalid type ({type(settings[key])}). Resetting to default.")
                    settings[key] = default_settings[key]
                    updated = True

        allowed_providers = list(llm_models_config.get('providers', {}).keys())
        if not allowed_providers: allowed_providers = ['gemini']
        if settings.get('llm_provider') not in allowed_providers:
            print(f"Warning: Invalid 'llm_provider' value '{settings.get('llm_provider')}'. Resetting to default '{default_settings['llm_provider']}'.")
            settings['llm_provider'] = default_settings['llm_provider']
            updated = True

        
        available_flux_models_raw = []
        try:
            if os.path.exists('modelslist.json'):
                 with open('modelslist.json', 'r') as f: models_list_data = json.load(f)
                 if isinstance(models_list_data, dict):
                     for type_list in models_list_data.values():
                         if isinstance(type_list, list): available_flux_models_raw.extend([m for m in type_list if isinstance(m, str)])
                     available_flux_models_raw = list(set(available_flux_models_raw))
        except Exception as e: print(f"Warning: Could not load modelslist.json for Flux model validation: {e}")
        
        available_flux_models = {m.strip().lower(): m.strip() for m in available_flux_models_raw}

        available_sdxl_checkpoints_raw = []
        try:
            if os.path.exists('checkpointslist.json'):
                 with open('checkpointslist.json', 'r') as f: checkpoints_list_data = json.load(f)
                 if isinstance(checkpoints_list_data, dict):
                     if isinstance(checkpoints_list_data.get('checkpoints'), list):
                         available_sdxl_checkpoints_raw.extend([c for c in checkpoints_list_data['checkpoints'] if isinstance(c, str)])
                     else:
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
                model_type = model_type.strip().lower()
                model_name_from_setting = model_name_from_setting.strip()

            valid_current_model_found = False
            if model_type == "flux":
                if model_name_from_setting.lower() in available_flux_models:
                    
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
            elif model_type is None :
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
            elif current_selected_model_setting != settings['selected_model']:
                updated = True

        elif not current_selected_model_setting and (available_flux_models or available_sdxl_checkpoints):
            if available_flux_models: settings['selected_model'] = f"Flux: {next(iter(available_flux_models.values()))}"
            elif available_sdxl_checkpoints: settings['selected_model'] = f"SDXL: {next(iter(available_sdxl_checkpoints.values()))}"
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
            elif current_t5_clip != available_clips_t5.get(current_t5_clip_norm.lower()):
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


        selected_provider = settings.get('llm_provider', 'gemini')
        # valid_provider_models_raw = llm_models_config.get('providers', {}).get(selected_provider, {}).get('models', [])
        # valid_provider_models = {m.strip().lower(): m.strip() for m in valid_provider_models_raw}

        def validate_llm_model(provider_short_name):
            nonlocal updated
            model_key = f"llm_model_{provider_short_name}"
            current_llm_model_setting = settings.get(model_key)
            current_llm_model = current_llm_model_setting.strip() if isinstance(current_llm_model_setting, str) else None

            
            specific_provider_models_raw = llm_models_config.get('providers', {}).get(provider_short_name, {}).get('models', [])
            specific_provider_models_map = {m.strip().lower(): m.strip() for m in specific_provider_models_raw}


            if current_llm_model:
                if current_llm_model.lower() not in specific_provider_models_map:
                    print(f"⚠️ Warning: Selected {provider_short_name.capitalize()} model '{current_llm_model_setting}' invalid for this provider. Resetting.")
                    settings[model_key] = next(iter(specific_provider_models_map.values())) if specific_provider_models_map else default_settings[model_key]
                    updated = True
                elif current_llm_model_setting != specific_provider_models_map.get(current_llm_model.lower()):
                    settings[model_key] = specific_provider_models_map.get(current_llm_model.lower())
                    updated = True
            elif not current_llm_model and specific_provider_models_map:
                settings[model_key] = next(iter(specific_provider_models_map.values()))
                updated = True

        validate_llm_model('gemini')
        validate_llm_model('groq')
        validate_llm_model('openai')

        
        if 'default_sdxl_negative_prompt' in settings and isinstance(settings['default_sdxl_negative_prompt'], str):
            settings['default_sdxl_negative_prompt'] = settings['default_sdxl_negative_prompt'].strip()
        elif 'default_sdxl_negative_prompt' not in settings:
            settings['default_sdxl_negative_prompt'] = default_settings['default_sdxl_negative_prompt']
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
        "steps": 32,
        "selected_t5_clip": default_t5,
        "selected_clip_l": default_l,
        "selected_upscale_model": None,
        "selected_vae": None,
        "default_style": "off",
        "default_variation_mode": "weak",
        "default_batch_size": 1,
        "default_guidance": 3.5,
        "default_guidance_sdxl": 7.0,
        "default_sdxl_negative_prompt": "",
        "default_mp_size": "1",
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
    try:
        numeric_keys_float = ['default_guidance', 'default_guidance_sdxl', 'upscale_factor']
        numeric_keys_int = ['steps', 'default_batch_size']
        bool_keys = ['remix_mode', 'llm_enhancer_enabled']
        string_keys_to_strip = ['llm_provider', 'llm_model_gemini', 'llm_model_groq', 'llm_model_openai', 'selected_model', 'selected_t5_clip', 'selected_clip_l', 'selected_upscale_model', 'selected_vae', 'default_style', 'default_sdxl_negative_prompt']
        mp_size_key = 'default_mp_size'
        allowed_mp_sizes = ["0.25", "0.5", "1", "1.25", "1.5", "1.75", "2", "2.5", "3", "4"]
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
            elif key in valid_settings and valid_settings[key] is None and key not in ['selected_model', 'selected_t5_clip', 'selected_clip_l', 'selected_upscale_model', 'selected_vae']: # Allow None for model selections
                
                if defaults[key] is not None:
                    print(f"Warning: '{key}' is None but expects a string. Resetting to default.")
                    valid_settings[key] = defaults[key]


        allowed_providers = list(llm_models_config.get('providers', {}).keys())
        if not allowed_providers: allowed_providers = ['gemini']
        if valid_settings.get('llm_provider') not in allowed_providers:
            valid_settings['llm_provider'] = defaults['llm_provider']

        if mp_size_key in valid_settings:
            mp_val = str(valid_settings[mp_size_key])
            if mp_val not in allowed_mp_sizes: valid_settings[mp_size_key] = defaults[mp_size_key]
            else: valid_settings[mp_size_key] = mp_val

        if display_prompt_key in valid_settings:
            display_pref_val = str(valid_settings[display_prompt_key]).lower()
            if display_pref_val not in allowed_display_prompt_options: valid_settings[display_prompt_key] = defaults[display_prompt_key]
            else: valid_settings[display_prompt_key] = display_pref_val


        for key in defaults:
            if key not in valid_settings:
                print(f"Warning: Key '{key}' missing before saving. Adding default.")
                valid_settings[key] = defaults[key]

        with open(settings_file, 'w') as f:
            json.dump(valid_settings, f, indent=2)
    except OSError as e: print(f"Error writing {settings_file}: {e}")
    except TypeError as e: print(f"Type error while saving settings: {e}")
    except Exception as e: print(f"Unexpected error saving settings: {e}"); traceback.print_exc()


def get_model_choices():
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

    settings = load_settings()
    current_model_setting = settings.get('selected_model')
    if isinstance(current_model_setting, str): current_model_setting = current_model_setting.strip()

    flux_favorites_raw = flux_models_data.get('favorites', [])
    flux_favorites = [f.strip() for f in flux_favorites_raw if isinstance(f, str)]
    sdxl_favorites_raw = sdxl_checkpoints_data.get('favorites', [])
    sdxl_favorites = [f.strip() for f in sdxl_favorites_raw if isinstance(f, str)]
    added_values = set()

    def add_option(model_name_with_prefix, is_default=False, is_favorite=False, model_type_label=""):
        norm_prefix_val = model_name_with_prefix.strip()
        if norm_prefix_val in added_values: return
        label_parts = []
        if is_favorite: label_parts.append("⭐")
        if model_type_label: label_parts.append(f"[{model_type_label}]")
        actual_model_name = norm_prefix_val.split(":",1)[1].strip() if ":" in norm_prefix_val else norm_prefix_val
        label_parts.append(actual_model_name)
        option_label = " ".join(label_parts).strip()
        choices.append(discord.SelectOption(label=option_label[:100], value=norm_prefix_val, default=is_default))
        added_values.add(norm_prefix_val)

    if current_model_setting and isinstance(current_model_setting, str):
        model_type, actual_name = None, current_model_setting
        if ":" in current_model_setting:
             model_type, actual_name = current_model_setting.split(":",1)
             model_type = model_type.strip().lower(); actual_name = actual_name.strip()
        is_fav = (model_type == "flux" and actual_name in flux_favorites) or \
                 (model_type == "sdxl" and actual_name in sdxl_favorites)
        add_option(current_model_setting, is_default=True, is_favorite=is_fav, model_type_label=model_type.upper() if model_type else "")

    for model in flux_favorites: add_option(f"Flux: {model}", is_favorite=True, model_type_label="Flux")
    for model in sdxl_favorites: add_option(f"SDXL: {model}", is_favorite=True, model_type_label="SDXL")

    for model_type_key in ['safetensors', 'sft', 'gguf']:
        for model_raw in flux_models_data.get(model_type_key, []):
            if isinstance(model_raw, str): add_option(f"Flux: {model_raw.strip()}", model_type_label="Flux")
    all_sdxl_checkpoints_raw = []
    if isinstance(sdxl_checkpoints_data.get('checkpoints'), list): all_sdxl_checkpoints_raw = sdxl_checkpoints_data['checkpoints']
    else:
        for key, value in sdxl_checkpoints_data.items():
            if isinstance(value, list) and key != 'favorites': all_sdxl_checkpoints_raw.extend(value)
    all_sdxl_checkpoints_raw = sorted(list(set(c for c in all_sdxl_checkpoints_raw if isinstance(c, str))))
    for model_raw in all_sdxl_checkpoints_raw: add_option(f"SDXL: {model_raw.strip()}", model_type_label="SDXL")

    
    final_choices = []
    if current_model_setting and any(opt.value == current_model_setting for opt in choices):
        current_opt = next(opt for opt in choices if opt.value == current_model_setting)
        current_opt.default = True
        final_choices.append(current_opt)
        final_choices.extend([opt for opt in choices if opt.value != current_model_setting])
    else:
        final_choices = choices
        if final_choices and not any(opt.default for opt in final_choices):
            final_choices[0].default = True

    return final_choices[:25]


def get_clip_choices(clip_type):
    choices = []; clips = {}
    try:
        if not os.path.exists('cliplist.json'): return []
        with open('cliplist.json', 'r') as f: clips = json.load(f)
        if not isinstance(clips, dict): clips = {}
    except Exception as e: print(f"Error loading cliplist.json: {e}"); return []
    settings = load_settings(); key_name = f'selected_{clip_type}'; current_clip_setting = settings.get(key_name)
    current_clip = current_clip_setting.strip() if isinstance(current_clip_setting, str) else None
    favorites_data = clips.get('favorites', {}); favorites_raw = []
    if isinstance(favorites_data, dict):
        favorites_raw = favorites_data.get(clip_type, [])
        if not isinstance(favorites_raw, list): favorites_raw = []
    favorites = [f.strip() for f in favorites_raw if isinstance(f, str)]; added_values = set()
    if current_clip:
        is_fav = current_clip in favorites; options_label = f"{'⭐' if is_fav else ''} {current_clip}".strip()
        choices.append(discord.SelectOption(label=options_label[:100], value=current_clip, default=True)); added_values.add(current_clip)
    for clip_fav_raw in favorites:
        clip_fav = clip_fav_raw.strip()
        if clip_fav != current_clip: options_label = f"⭐ {clip_fav}".strip(); choices.append(discord.SelectOption(label=options_label[:100], value=clip_fav)); added_values.add(clip_fav)
        if len(choices) >= 25: break
    if len(choices) < 25:
        clip_list_raw = clips.get(clip_type, [])
        if isinstance(clip_list_raw, list):
            for clip_raw in clip_list_raw:
                clip = clip_raw.strip() if isinstance(clip_raw, str) else None
                if clip and clip not in added_values: choices.append(discord.SelectOption(label=clip[:100], value=clip)); added_values.add(clip)
                if len(choices) >= 25: break
    
    final_choices = []
    if current_clip and any(opt.value == current_clip for opt in choices):
        current_opt = next(opt for opt in choices if opt.value == current_clip); current_opt.default = True
        final_choices.append(current_opt); final_choices.extend([opt for opt in choices if opt.value != current_clip])
    else:
        final_choices = choices
        if final_choices and not any(opt.default for opt in final_choices): final_choices[0].default = True
    return final_choices[:25]

def get_t5_clip_choices(): return get_clip_choices('t5')
def get_clip_l_choices(): return get_clip_choices('clip_L')


def get_style_choices():
    choices = []; styles = load_styles_config(); settings = load_settings()
    current_style = settings.get('default_style', 'off').strip()
    favorite_styles = []; other_styles = []; current_option = None; off_option = None
    for style_raw, data_raw in styles.items():
        style = style_raw.strip() if isinstance(style_raw, str) else None
        if not style or not isinstance(data_raw, dict): continue
        data = {k.strip() if isinstance(k, str) else k: v for k,v in data_raw.items()}
        is_favorite = data.get('favorite', False)
        label_prefix = "⭐" if is_favorite and style != "off" else ("🔴" if style == "off" else "")
        option_label = f"{label_prefix} {style}".strip()
        option = discord.SelectOption(label=option_label[:100], value=style)
        if style == current_style: option.default = True; current_option = option
        elif style == "off": off_option = option
        elif is_favorite: favorite_styles.append(option)
        else: other_styles.append(option)
    if current_option: choices.append(current_option)
    if off_option and current_style != "off": choices.append(off_option)
    elif off_option and not current_option and 'off' in styles: choices.append(off_option)
    favorite_styles.sort(key=lambda opt: opt.label.lstrip('⭐🔴 ')); other_styles.sort(key=lambda opt: opt.label)
    choices.extend(favorite_styles); choices.extend(other_styles)
    if 'off' not in [opt.value for opt in choices] and 'off' in styles:
         if off_option: choices.append(off_option)
         else: choices.append(discord.SelectOption(label="🔴 off", value="off"))
    seen_values = set(); unique_choices = []
    for option in choices:
        if option.value not in seen_values: unique_choices.append(option); seen_values.add(option.value)
    
    final_choices = []
    if current_option and any(opt.value == current_option.value for opt in unique_choices):
        
        current_opt_from_unique = next(opt for opt in unique_choices if opt.value == current_option.value)
        current_opt_from_unique.default = True
        final_choices.append(current_opt_from_unique)
        final_choices.extend([opt for opt in unique_choices if opt.value != current_option.value])
    else:
        final_choices = unique_choices
        if final_choices and not any(opt.default for opt in final_choices) : final_choices[0].default = True

    return final_choices[:25]


def get_steps_choices():
    settings = load_settings()
    try: current_steps = int(settings.get('steps', 32))
    except (ValueError, TypeError): current_steps = 32
    steps_options = sorted(list(set([4, 8, 16, 24, 32, 40, 48, 56, 64] + [current_steps])))
    choices = [discord.SelectOption(label=f"{s} Steps", value=str(s), default=(s == current_steps)) for s in steps_options]
    if choices and not any(o.default for o in choices) and current_steps in steps_options:
        for opt in choices:
            if int(opt.value) == current_steps: opt.default = True; break
    if choices and not any(o.default for o in choices): choices[0].default = True
    return choices[:25]

def get_guidance_choices():
    settings = load_settings()
    try: current_guidance = float(settings.get('default_guidance', 3.5))
    except (ValueError, TypeError): current_guidance = 3.5
    guidance_values_formatted = [f"{g:.1f}" for g in np.arange(0.0, 10.1, 0.5)]
    current_guidance_str = f"{current_guidance:.1f}"
    if current_guidance_str not in guidance_values_formatted:
        guidance_values_formatted.append(current_guidance_str)
        guidance_values_formatted.sort(key=float)
    choices = [discord.SelectOption(label=f"Guidance (Flux): {g}", value=g, default=(abs(float(g) - current_guidance) < 0.01)) for g in guidance_values_formatted]
    if choices and not any(o.default for o in choices) and current_guidance_str in guidance_values_formatted:
        for opt in choices:
            if opt.value == current_guidance_str: opt.default = True; break
    if choices and not any(o.default for o in choices): choices[0].default = True
    return choices[:25]

def get_sdxl_guidance_choices():
    settings = load_settings()
    try: current_guidance_sdxl = float(settings.get('default_guidance_sdxl', 7.0))
    except (ValueError, TypeError): current_guidance_sdxl = 7.0
    guidance_values_formatted = [f"{g:.1f}" for g in np.arange(1.0, 15.1, 0.5)]
    current_guidance_sdxl_str = f"{current_guidance_sdxl:.1f}"
    if current_guidance_sdxl_str not in guidance_values_formatted:
        guidance_values_formatted.append(current_guidance_sdxl_str)
        guidance_values_formatted.sort(key=float)
    choices = [discord.SelectOption(label=f"Guidance (SDXL): {g}", value=g, default=(abs(float(g) - current_guidance_sdxl) < 0.01)) for g in guidance_values_formatted]
    if choices and not any(o.default for o in choices) and current_guidance_sdxl_str in guidance_values_formatted:
        for opt in choices:
            if opt.value == current_guidance_sdxl_str: opt.default = True; break
    if choices and not any(o.default for o in choices): choices[0].default = True
    return choices[:25]

def get_variation_mode_choices():
    settings = load_settings(); current_mode = settings.get('default_variation_mode', 'weak')
    return [discord.SelectOption(label=f"{m.capitalize()} Variation", value=m, default=(m == current_mode)) for m in ["weak", "strong"]]

def get_batch_size_choices():
    settings = load_settings()
    try: current_size = int(settings.get('default_batch_size', 1))
    except(ValueError, TypeError): current_size = 1
    return [discord.SelectOption(label=f"Batch Size: {s}", value=str(s), default=(s == current_size)) for s in [1, 2, 3, 4]]

def get_remix_mode_choices():
    settings = load_settings(); current_value = settings.get('remix_mode', False)
    return [discord.SelectOption(label="Remix Mode: OFF", value="False", default=not current_value), discord.SelectOption(label="Remix Mode: ON", value="True", default=current_value)]

def get_upscale_factor_choices():
    settings = load_settings()
    try: current_factor = float(settings.get('upscale_factor', 1.85))
    except (ValueError, TypeError): current_factor = 1.85
    factor_values_formatted = [f"{f:.1f}" for f in np.arange(1.5, 4.01, 0.5)]
    current_factor_str = f"{current_factor:.1f}"
    if current_factor_str not in factor_values_formatted:
        factor_values_formatted.append(current_factor_str); factor_values_formatted.sort(key=float)
    choices = [discord.SelectOption(label=f"Upscale Factor: {f}x", value=f, default=(abs(float(f) - current_factor) < 0.01)) for f in factor_values_formatted]
    if choices and not any(o.default for o in choices) and current_factor_str in factor_values_formatted:
        for opt in choices:
             if opt.value == current_factor_str: opt.default = True; break
    if choices and not any(o.default for o in choices): choices[0].default = True
    return choices[:25]

def get_llm_enhancer_choices():
    settings = load_settings(); current_value = settings.get('llm_enhancer_enabled', False)
    return [discord.SelectOption(label="LLM Prompt Enhancer: OFF", value="False", default=not current_value), discord.SelectOption(label="LLM Prompt Enhancer: ON", value="True", default=current_value)]

def get_llm_provider_choices():
    settings = load_settings(); current_provider = settings.get('llm_provider', 'gemini')
    providers = llm_models_config.get('providers', {})
    options = [discord.SelectOption(label=d.get("display_name", k), value=k, default=(k == current_provider)) for k, d in providers.items()]
    if options and not any(o.default for o in options):
        found = any(opt.value == current_provider for opt in options)
        if found: next(opt for opt in options if opt.value == current_provider).default = True
        elif options: options[0].default = True
    return options

def get_llm_model_choices(provider=None):
    settings = load_settings()
    if provider is None: provider = settings.get('llm_provider', 'gemini')
    provider_data = llm_models_config.get('providers', {}).get(provider, {})
    models_raw = provider_data.get('models', [])
    models = [m.strip() for m in models_raw if isinstance(m, str)]
    if not models:
         provider_display = provider_data.get("display_name", provider.capitalize())
         return [discord.SelectOption(label=f"No models for {provider_display}", value="none", default=True)]
    current_model_key = f"llm_model_{provider}"; current_model_setting = settings.get(current_model_key)
    current_model = current_model_setting.strip() if isinstance(current_model_setting, str) else None
    if current_model and current_model not in models: models = [current_model] + [m for m in models if m != current_model]
    options = [discord.SelectOption(label=m[:100], value=m, default=(m == current_model)) for m in models]
    options.sort(key=lambda o: (not o.default, o.label))
    if options and not any(o.default for o in options) and current_model in models:
        next(opt for opt in options if opt.value == current_model).default = True
    if options and not any(o.default for o in options): options[0].default = True
    return options[:25]

def get_mp_size_choices():
    settings = load_settings(); current_size = str(settings.get('default_mp_size', "1")).strip()
    allowed_sizes = ["0.25", "0.5", "1", "1.25", "1.5", "1.75", "2", "2.5", "3", "4"]
    if current_size not in allowed_sizes:
        try:
            current_size_float = float(current_size)
            for allowed in allowed_sizes:
                if abs(float(allowed) - current_size_float) < 1e-6: current_size = allowed; break
            else: current_size = "1"
        except Exception: current_size = "1"
    size_labels = {"0.25": "0.25MP (~512x512)", "0.5": "0.5MP (~768x768)", "1": "1MP (~1024x1024)", "1.25": "1.25MP (~1280x1024)", "1.5": "1.5MP (~1440x1024)", "1.75": "1.75MP (~1600x1024)", "2": "2MP (~1920x1080)", "2.5": "2.5MP (~1536x1536)", "3": "3MP (~1792x1792)", "4": "4MP (~2048x2048)"}
    return [discord.SelectOption(label=size_labels.get(s, f"{s} MP"), value=s, default=(s == current_size)) for s in allowed_sizes]

def get_upscale_model_choices():
    choices = []; models_data = {};
    try:
        from comfyui_api import get_available_comfyui_models
        models_data = get_available_comfyui_models()
    except Exception: pass
    upscale_models_raw = []
    if isinstance(models_data, dict):
        upscale_models_raw.extend(models_data.get('upscaler', []))
        if not upscale_models_raw: upscale_models_raw.extend(models_data.get('unet', [])) # Fallback
    upscale_models = sorted(list(set(u.strip() for u in upscale_models_raw if isinstance(u, str))))
    settings = load_settings(); current_upscale_model_setting = settings.get('selected_upscale_model')
    current_upscale_model = current_upscale_model_setting.strip() if isinstance(current_upscale_model_setting, str) else None
    added_values = set()
    if current_upscale_model:
        is_available = current_upscale_model in upscale_models
        label = current_upscale_model
        if not is_available and upscale_models : label += " (Custom?)"
        choices.append(discord.SelectOption(label=label[:100], value=current_upscale_model, default=True))
        added_values.add(current_upscale_model)
    for model in upscale_models:
        if model not in added_values: choices.append(discord.SelectOption(label=model[:100], value=model)); added_values.add(model)
        if len(choices) >= 25: break
    if not choices: choices.append(discord.SelectOption(label="None Available/Selected", value="None", default=True if not current_upscale_model else False))
    elif choices and not any(c.default for c in choices): choices[0].default = True
    return choices[:25]


def get_vae_choices():
    choices = []; models_data = {}
    try:
        from comfyui_api import get_available_comfyui_models
        models_data = get_available_comfyui_models()
    except Exception: pass
    vae_models_raw = models_data.get('vae', []) if isinstance(models_data, dict) else []
    vae_models = sorted(list(set(v.strip() for v in vae_models_raw if isinstance(v, str))))
    settings = load_settings(); current_vae_setting = settings.get('selected_vae')
    current_vae = current_vae_setting.strip() if isinstance(current_vae_setting, str) else None
    added_values = set()
    if current_vae:
        is_available = current_vae in vae_models; label = current_vae
        if not is_available and vae_models: label += " (Custom?)"
        choices.append(discord.SelectOption(label=label[:100], value=current_vae, default=True)); added_values.add(current_vae)
    for vae in vae_models:
        if vae not in added_values: choices.append(discord.SelectOption(label=vae[:100], value=vae)); added_values.add(vae)
        if len(choices) >= 25: break
    if not choices: choices.append(discord.SelectOption(label="None Available/Selected", value="None", default=True if not current_vae else False))
    elif choices and not any(c.default for c in choices): choices[0].default = True
    return choices[:25]

def get_display_prompt_preference_choices():
    settings = load_settings(); current_preference = settings.get('display_prompt_preference', 'enhanced')
    return [discord.SelectOption(label="Show Enhanced Prompt ✨", value="enhanced", default=(current_preference == 'enhanced')), discord.SelectOption(label="Show Original Prompt ✍️", value="original", default=(current_preference == 'original'))]
