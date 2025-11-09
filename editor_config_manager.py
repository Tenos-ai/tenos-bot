# --- START OF FILE editor_config_manager.py ---
import json
import os
import traceback
from datetime import datetime
from tkinter import scrolledtext, BooleanVar

from editor_utils import load_json_config, save_json_config, silent_showerror
from editor_constants import CONFIG_FILE_NAME, SETTINGS_FILE_NAME
from settings_shared import (
    WAN_CHECKPOINT_KEY,
    WAN_I2V_HIGH_NOISE_KEY,
    WAN_I2V_LOW_NOISE_KEY,
    WAN_T2V_HIGH_NOISE_KEY,
    WAN_T2V_LOW_NOISE_KEY,
    sync_wan_checkpoint_alias,
)

class EditorConfigManager:
    """
    Manages the loading, validation, and saving of main configuration (config.json)
    and bot settings (settings.json) for the ConfigEditor.
    """
    def __init__(self, editor_app_ref):
        self.editor_app = editor_app_ref
        self.config = {}
        self.settings = {}
        self.llm_models_data_for_settings_template = {}
        
        self.settings_last_mtime = 0

        self.config_template_definition = {
            "OUTPUTS": {"UPSCALES": "", "VARIATIONS": "", "GENERATIONS": ""},
            "MODELS": {
                "MODEL_FILES": "",
                "CHECKPOINTS_FOLDER": "",
                "QWEN_MODELS": "",
                "WAN_MODELS": "",
                "UPSCALE_MODELS": "",
                "VAE_MODELS": "",
            },
            "TEXT_ENCODERS": {
                "QWEN_TEXT_ENCODERS": "",
                "WAN_TEXT_ENCODERS": "",
                "WAN_VISION_ENCODERS": "",
            },
            "CLIP": {"CLIP_FILES": ""},
            "LORAS": {"LORA_FILES": ""},
            "NODES": {"CUSTOM_NODES": ""},
            "COMFYUI_API": {"HOST": "127.0.0.1", "PORT": 8188},
            "BOT_INTERNAL_API": {"HOST": "127.0.0.1", "PORT": 8189, "AUTH_TOKEN": ""},
            "BOT_API": {"KEY": ""},
            "ADMIN": {"USERNAME": "", "ID": ""},
            "ALLOWED_USERS": {},
            "LLM_ENHANCER": {"OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "GROQ_API_KEY": ""},
            "APP_SETTINGS": {
                "AUTO_UPDATE_ON_STARTUP": False,
                "STATUS_NOTIFICATION_STYLE": "timed",
                "STATUS_NOTIFICATION_DURATION_MS": 2000,
            }
        }
        def _build_settings_template():
            template = {
             "selected_model": None,
             "active_model_family": "flux",
             "selected_kontext_model": None,
             "default_flux_model": None,
             "default_flux_vae": None,
            "default_sdxl_checkpoint": None,
            "default_sdxl_clip": None,
            "default_sdxl_vae": None,
            "default_qwen_checkpoint": None,
            WAN_CHECKPOINT_KEY: None,
            WAN_T2V_HIGH_NOISE_KEY: "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
            WAN_T2V_LOW_NOISE_KEY: "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors",
            WAN_I2V_HIGH_NOISE_KEY: "wan2.2_i2v_high_noise_14B_fp16.safetensors",
            WAN_I2V_LOW_NOISE_KEY: "wan2.2_i2v_low_noise_14B_fp16.safetensors",
            "default_wan_low_noise_unet": "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors",
            "default_qwen_clip": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
            "default_qwen_vae": "qwen_image_vae.safetensors",
            "default_qwen_edit_checkpoint": None,
            "default_qwen_edit_clip": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
            "default_qwen_edit_vae": "qwen_image_vae.safetensors",
            "default_qwen_shift": 0.0,
            "default_wan_clip": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "default_wan_vae": "wan2.2_vae.safetensors",
            "default_wan_vision_clip": "clip_vision_h.safetensors",
            "default_wan_shift": 8.0,
             "steps": 32,
             "sdxl_steps": 26,
             "qwen_steps": 28,
             "wan_steps": 30,
             "selected_t5_clip": None,
             "selected_clip_l": None,
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
             "qwen_ksampler_cfg": 5.5,
             "qwen_ksampler_denoise": 1.0,
            "qwen_edit_ksampler_sampler": "euler",
            "qwen_edit_ksampler_scheduler": "normal",
             "qwen_edit_ksampler_cfg": 5.5,
             "qwen_edit_ksampler_denoise": 0.6,
             "qwen_edit_cfg_rescale": 1.0,
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
             "qwen_upscale_cfg": 5.5,
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
             "default_guidance_qwen": 5.5,
             "default_guidance_wan": 6.0,
             "default_sdxl_negative_prompt": "",
             "default_qwen_negative_prompt": "",
             "default_wan_negative_prompt": "",
             "default_mp_size": 1.0,
            "qwen_edit_steps": 28,
            "default_guidance_qwen_edit": 5.5,
            "default_qwen_edit_negative_prompt": "",
            "qwen_edit_denoise": 0.6,
            "qwen_edit_shift": 0.0,
             "kontext_guidance": 3.0,
             "kontext_steps": 32,
             "kontext_mp_size": 1.15,
             "remix_mode": False,
             "upscale_factor": 1.85,
             "llm_enhancer_enabled": False,
             "llm_provider": "gemini",
             "llm_model_gemini": self._get_default_llm_model_for_provider("gemini", "gemini-1.5-flash"),
             "llm_model_groq": self._get_default_llm_model_for_provider("groq", "llama3-8b-8192"),
             "llm_model_openai": self._get_default_llm_model_for_provider("openai", "gpt-3.5-turbo"),
             "display_prompt_preference": "enhanced",
             "default_editing_mode": "kontext",
             "wan_animation_resolution": "512x512",
             "wan_animation_duration": 33,
             "wan_animation_motion_profile": "medium"
            }

            sync_wan_checkpoint_alias(template)
            return template

        self.settings_template_factory = _build_settings_template

    def _get_default_llm_model_for_provider(self, provider_key, fallback_model_name):
        if not self.llm_models_data_for_settings_template:
            return fallback_model_name
        provider_info = self.llm_models_data_for_settings_template.get('providers', {}).get(provider_key, {})
        models_list = provider_info.get('models', [])
        return models_list[0] if models_list else fallback_model_name

    def load_main_config_data(self):
        loaded_config_from_file = load_json_config(
            CONFIG_FILE_NAME,
            lambda: self.config_template_definition.copy(),
            "main application config"
        )
        merged_config_result = self.config_template_definition.copy()
        was_config_updated_during_load = False

        if "MODELS" not in loaded_config_from_file: loaded_config_from_file["MODELS"] = {}
        if "COMFYUI_API" not in loaded_config_from_file: loaded_config_from_file["COMFYUI_API"] = {}
        
        if "UPSCALE_MODELS" in loaded_config_from_file and isinstance(loaded_config_from_file["UPSCALE_MODELS"], str):
            if "UPSCALE_MODELS" not in loaded_config_from_file["MODELS"]: loaded_config_from_file["MODELS"]["UPSCALE_MODELS"] = loaded_config_from_file.pop("UPSCALE_MODELS"); was_config_updated_during_load = True
        if "VAE_MODELS" in loaded_config_from_file and isinstance(loaded_config_from_file["VAE_MODELS"], str):
            if "VAE_MODELS" not in loaded_config_from_file["MODELS"]: loaded_config_from_file["MODELS"]["VAE_MODELS"] = loaded_config_from_file.pop("VAE_MODELS"); was_config_updated_during_load = True
        if "COMFYUI_HOST" in loaded_config_from_file:
            if "HOST" not in loaded_config_from_file["COMFYUI_API"]: loaded_config_from_file["COMFYUI_API"]["HOST"] = loaded_config_from_file.pop("COMFYUI_HOST"); was_config_updated_during_load = True
        if "COMFYUI_PORT" in loaded_config_from_file:
            if "PORT" not in loaded_config_from_file["COMFYUI_API"]: loaded_config_from_file["COMFYUI_API"]["PORT"] = loaded_config_from_file.pop("COMFYUI_PORT"); was_config_updated_during_load = True

        for section_key_template, template_section_val in self.config_template_definition.items():
            if section_key_template in loaded_config_from_file:
                if isinstance(template_section_val, dict):
                    if isinstance(loaded_config_from_file[section_key_template], dict):
                        merged_config_result[section_key_template] = template_section_val.copy()
                        for item_key_loaded, loaded_item_val in loaded_config_from_file[section_key_template].items():
                            merged_config_result[section_key_template][item_key_loaded] = loaded_item_val
                        for sub_key_in_template in template_section_val:
                            if sub_key_in_template not in merged_config_result[section_key_template]:
                                merged_config_result[section_key_template][sub_key_in_template] = template_section_val[sub_key_in_template]
                                was_config_updated_during_load = True
                    else: was_config_updated_during_load = True
                else: merged_config_result[section_key_template] = loaded_config_from_file[section_key_template]
            else: was_config_updated_during_load = True

        legacy_settings_data = None
        try:
            if os.path.exists(SETTINGS_FILE_NAME):
                with open(SETTINGS_FILE_NAME, 'r') as legacy_settings_file:
                    potential_settings = json.load(legacy_settings_file)
                if isinstance(potential_settings, dict):
                    legacy_settings_data = potential_settings
        except (OSError, json.JSONDecodeError):
            legacy_settings_data = None
        except Exception:
            legacy_settings_data = None

        if legacy_settings_data is not None:
            app_settings_section = merged_config_result.setdefault("APP_SETTINGS", self.config_template_definition["APP_SETTINGS"].copy())
            legacy_style_value = legacy_settings_data.pop('status_notification_style', None)
            if legacy_style_value is not None:
                normalized_style = str(legacy_style_value).lower()
                if normalized_style not in {"timed", "sticky"}:
                    normalized_style = self.config_template_definition["APP_SETTINGS"]["STATUS_NOTIFICATION_STYLE"]
                if app_settings_section.get("STATUS_NOTIFICATION_STYLE") != normalized_style:
                    app_settings_section["STATUS_NOTIFICATION_STYLE"] = normalized_style
                    was_config_updated_during_load = True
            legacy_duration_value = legacy_settings_data.pop('status_notification_duration_ms', None)
            if legacy_duration_value is not None:
                try:
                    duration_int = int(legacy_duration_value)
                except (TypeError, ValueError):
                    duration_int = self.config_template_definition["APP_SETTINGS"]["STATUS_NOTIFICATION_DURATION_MS"]
                duration_int = max(500, min(60000, duration_int))
                if app_settings_section.get("STATUS_NOTIFICATION_DURATION_MS") != duration_int:
                    app_settings_section["STATUS_NOTIFICATION_DURATION_MS"] = duration_int
                    was_config_updated_during_load = True
            if 'status_notification_style' in legacy_settings_data or 'status_notification_duration_ms' in legacy_settings_data:
                legacy_settings_data.pop('status_notification_style', None)
                legacy_settings_data.pop('status_notification_duration_ms', None)
            save_json_config(SETTINGS_FILE_NAME, legacy_settings_data, "bot settings")

        self.config = merged_config_result
        if was_config_updated_during_load:
            self.save_main_config_data(show_success_message=False)

    def save_main_config_data(self, show_success_message=True):
        config_to_write = {}
        try:
            for section_key, section_value in self.config_template_definition.items():
                if section_key in ["ADMIN", "ALLOWED_USERS"]:
                    config_to_write[section_key] = self.config.get(section_key, section_value)
                    continue

                if isinstance(section_value, dict):
                    config_to_write[section_key] = {}
                    for sub_key in section_value:
                        ui_var_name = f"{section_key}.{sub_key}"
                        if ui_var_name in self.editor_app.config_vars:
                            tk_var = self.editor_app.config_vars[ui_var_name]
                            value_from_ui = tk_var.get()
                            if (section_key == "COMFYUI_API" or section_key == "BOT_INTERNAL_API") and sub_key == "PORT":
                                try: config_to_write[section_key][sub_key] = int(value_from_ui)
                                except (ValueError, TypeError): config_to_write[section_key][sub_key] = self.config_template_definition[section_key][sub_key]
                            elif section_key == "APP_SETTINGS" and sub_key == "STATUS_NOTIFICATION_STYLE":
                                style_val = str(value_from_ui).lower()
                                config_to_write[section_key][sub_key] = style_val if style_val in ["timed", "sticky"] else "timed"
                            elif section_key == "APP_SETTINGS" and sub_key == "STATUS_NOTIFICATION_DURATION_MS":
                                try:
                                    duration_val = int(value_from_ui)
                                except (ValueError, TypeError):
                                    duration_val = self.config_template_definition[section_key][sub_key]
                                config_to_write[section_key][sub_key] = max(500, min(60000, duration_val))
                            elif isinstance(tk_var, BooleanVar):
                                config_to_write[section_key][sub_key] = value_from_ui
                            else: config_to_write[section_key][sub_key] = value_from_ui if value_from_ui is not None else ""
                        else: config_to_write[section_key][sub_key] = self.config.get(section_key, {}).get(sub_key, "")
                else:
                    if section_key in self.editor_app.config_vars:
                        value_from_ui = self.editor_app.config_vars[section_key].get()
                        config_to_write[section_key] = value_from_ui if value_from_ui is not None else ""
                    else: config_to_write[section_key] = self.config.get(section_key, section_value)

            if save_json_config(CONFIG_FILE_NAME, config_to_write, "main application config"):
                self.config = config_to_write
                if show_success_message:
                    if hasattr(self.editor_app, 'main_config_status_var'):
                        self.editor_app.main_config_status_var.set(f"Saved at {datetime.now().strftime('%H:%M:%S')}")
                    self.editor_app.show_status_message("Main configuration saved successfully!", level="success")
                    self.editor_app.master.after(50, self.editor_app.refresh_all_ui_tabs)
        except Exception as e_save:
            self.editor_app.show_status_message(f"Failed to save main config: {str(e_save)}", level="error", duration=2200)
            traceback.print_exc()


    def load_bot_settings_data(self, llm_models_data_param):
        self.llm_models_data_for_settings_template = llm_models_data_param
        current_settings_template = self.settings_template_factory()
        loaded_settings_from_file = load_json_config(SETTINGS_FILE_NAME, lambda: current_settings_template.copy(), "bot settings")
        
        # Migrate old 'default_style' key
        if 'default_style' in loaded_settings_from_file:
            old_style = loaded_settings_from_file.pop('default_style')
            if 'default_style_flux' not in loaded_settings_from_file:
                loaded_settings_from_file['default_style_flux'] = old_style
            if 'default_style_sdxl' not in loaded_settings_from_file:
                loaded_settings_from_file['default_style_sdxl'] = old_style
        
        merged_settings_result = current_settings_template.copy()
        was_settings_updated_during_load = False
        for key_template, template_default_val in current_settings_template.items():
            if key_template in loaded_settings_from_file:
                value_from_loaded_file = loaded_settings_from_file[key_template]
                try:
                    if key_template == 'display_prompt_preference':
                        str_val = str(value_from_loaded_file).lower()
                        allowed_display = ['enhanced', 'original']
                        merged_settings_result[key_template] = str_val if str_val in allowed_display else template_default_val
                        if merged_settings_result[key_template] != str_val: was_settings_updated_during_load = True
                    elif key_template == 'default_sdxl_negative_prompt':
                        merged_settings_result[key_template] = str(value_from_loaded_file) if value_from_loaded_file is not None else ""
                    elif isinstance(template_default_val, float): merged_settings_result[key_template] = float(value_from_loaded_file)
                    elif isinstance(template_default_val, int): merged_settings_result[key_template] = int(value_from_loaded_file)
                    elif isinstance(template_default_val, bool):
                        merged_settings_result[key_template] = str(value_from_loaded_file).lower() in ['true', '1', 't', 'y', 'yes', 'on'] if isinstance(value_from_loaded_file, str) else bool(value_from_loaded_file)
                    elif isinstance(template_default_val, str) or template_default_val is None:
                         merged_settings_result[key_template] = str(value_from_loaded_file) if value_from_loaded_file is not None else None
                    else: merged_settings_result[key_template] = value_from_loaded_file
                except (ValueError, TypeError):
                    merged_settings_result[key_template] = template_default_val; was_settings_updated_during_load = True
            else: was_settings_updated_during_load = True
        selected_llm_provider = merged_settings_result.get('llm_provider')
        valid_llm_providers = list(self.llm_models_data_for_settings_template.get('providers', {}).keys())
        if not valid_llm_providers: valid_llm_providers = ['gemini']
        if selected_llm_provider not in valid_llm_providers:
            merged_settings_result['llm_provider'] = current_settings_template['llm_provider']
            selected_llm_provider = merged_settings_result['llm_provider']
            was_settings_updated_during_load = True
        for prov_key_check in valid_llm_providers:
            model_setting_key_to_check = f"llm_model_{prov_key_check}"
            valid_models_for_this_provider = self.llm_models_data_for_settings_template.get('providers',{}).get(prov_key_check,{}).get('models',[])
            current_model_for_this_provider = merged_settings_result.get(model_setting_key_to_check)
            if current_model_for_this_provider not in valid_models_for_this_provider:
                new_default_model = valid_models_for_this_provider[0] if valid_models_for_this_provider else current_settings_template.get(model_setting_key_to_check)
                merged_settings_result[model_setting_key_to_check] = new_default_model
                was_settings_updated_during_load = True
        sync_wan_checkpoint_alias(merged_settings_result)
        self.settings = merged_settings_result
        if was_settings_updated_during_load:
            self.save_bot_settings_data(show_success_message=False)
        else:
            try:
                if os.path.exists(SETTINGS_FILE_NAME): self.settings_last_mtime = os.path.getmtime(SETTINGS_FILE_NAME)
            except OSError: self.settings_last_mtime = 0

    def save_bot_settings_data(self, show_success_message=True):
        try:
            current_settings_template_for_save = self.settings_template_factory()
            settings_to_write = current_settings_template_for_save.copy()
            float_bounds = {
                'default_qwen_shift': (0.0, 10.0),
                'qwen_edit_shift': (0.0, 10.0),
                'default_wan_shift': (0.0, 10.0),
                'qwen_edit_denoise': (0.0, 1.0),
                'default_guidance_qwen_edit': (0.0, 20.0),
            }
            for key_to_save in settings_to_write:
                if key_to_save in self.editor_app.settings_vars:
                    ui_var_instance = self.editor_app.settings_vars[key_to_save]
                    ui_widget_instance = self.editor_app.bot_settings_widgets.get(key_to_save)
                    value_from_ui = None
                    if isinstance(ui_widget_instance, scrolledtext.ScrolledText): value_from_ui = ui_widget_instance.get("1.0", "end-1c").strip()
                    else: value_from_ui = ui_var_instance.get()
                    if key_to_save == 'llm_provider':
                        selected_display_name = value_from_ui
                        provider_internal_key = next((k_prov for k_prov, v_disp in self.editor_app.provider_display_map.items() if v_disp == selected_display_name), None)
                        settings_to_write[key_to_save] = provider_internal_key if provider_internal_key else selected_display_name.lower()
                    elif key_to_save == 'llm_model': continue
                    elif key_to_save == 'display_prompt_preference':
                        internal_pref_value = next((k_pref for k_pref, v_pref_disp in self.editor_app.display_prompt_map.items() if v_pref_disp == value_from_ui), 'enhanced')
                        settings_to_write[key_to_save] = internal_pref_value
                    elif isinstance(current_settings_template_for_save.get(key_to_save), float):
                        try:
                            numeric_val = float(value_from_ui)
                        except (TypeError, ValueError):
                            numeric_val = current_settings_template_for_save[key_to_save]
                        bounds = float_bounds.get(key_to_save)
                        if bounds:
                            min_val, max_val = bounds
                            if numeric_val < min_val:
                                numeric_val = min_val
                            if numeric_val > max_val:
                                numeric_val = max_val
                        settings_to_write[key_to_save] = numeric_val
                    elif isinstance(current_settings_template_for_save.get(key_to_save), int): settings_to_write[key_to_save] = int(value_from_ui)
                    elif isinstance(current_settings_template_for_save.get(key_to_save), bool):
                        if isinstance(value_from_ui, str):
                            settings_to_write[key_to_save] = value_from_ui.lower() in ['true', '1', 't', 'y', 'yes', 'on']
                        else:
                            settings_to_write[key_to_save] = bool(value_from_ui)
                    else: settings_to_write[key_to_save] = str(value_from_ui) if value_from_ui is not None else None
            saved_provider = settings_to_write.get('llm_provider', 'gemini')
            if 'llm_model' in self.editor_app.settings_vars:
                model_for_current_provider = self.editor_app.settings_vars['llm_model'].get()
                settings_to_write[f"llm_model_{saved_provider}"] = model_for_current_provider
            settings_to_write.pop('llm_model', None)
            sync_wan_checkpoint_alias(settings_to_write)
            if save_json_config(SETTINGS_FILE_NAME, settings_to_write, "bot settings"):
                self.settings = settings_to_write
                try: self.settings_last_mtime = os.path.getmtime(SETTINGS_FILE_NAME)
                except OSError as e_mtime: self.settings_last_mtime = 0
                if show_success_message:
                    if hasattr(self.editor_app, 'bot_settings_status_var'):
                        self.editor_app.bot_settings_status_var.set(f"Saved at {datetime.now().strftime('%H:%M:%S')}")
                    self.editor_app.show_status_message("Bot settings saved successfully!", level="success")
        except Exception as e_save_settings:
            self.editor_app.show_status_message(f"Failed to save bot settings: {str(e_save_settings)}", level="error", duration=2200)
            traceback.print_exc()
# --- END OF FILE editor_config_manager.py ---
