import json
import os
import traceback
from tkinter import scrolledtext

from editor_utils import load_json_config, save_json_config, silent_showerror, silent_showinfo
from editor_constants import CONFIG_FILE_NAME, SETTINGS_FILE_NAME

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
            "MODELS": {"MODEL_FILES": "", "CHECKPOINTS_FOLDER": "", "UPSCALE_MODELS": "", "VAE_MODELS": ""},
            "CLIP": {"CLIP_FILES": ""},
            "LORAS": {"LORA_FILES": ""},
            "NODES": {"CUSTOM_NODES": ""},
            "COMFYUI_API": {"HOST": "127.0.0.1", "PORT": 8188},
            "BOT_INTERNAL_API": {"HOST": "127.0.0.1", "PORT": 8189},
            "BOT_API": {"KEY": ""},
            "ADMIN": {"USERNAME": ""},
            "ALLOWED_USERS": {},
            "LLM_ENHANCER": {"OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "GROQ_API_KEY": ""},
        }
        self.settings_template_factory = lambda: {
             "selected_model": None, 
             "selected_kontext_model": None,
             "steps": 32, 
             "selected_t5_clip": None,
             "selected_clip_l": None, 
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
             "llm_model_gemini": self._get_default_llm_model_for_provider("gemini", "gemini-1.5-flash"),
             "llm_model_groq": self._get_default_llm_model_for_provider("groq", "llama3-8b-8192"),
             "llm_model_openai": self._get_default_llm_model_for_provider("openai", "gpt-3.5-turbo"),
             "display_prompt_preference": "enhanced"
        }

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
                            value_from_ui = self.editor_app.config_vars[ui_var_name].get()
                            if (section_key == "COMFYUI_API" or section_key == "BOT_INTERNAL_API") and sub_key == "PORT":
                                try: config_to_write[section_key][sub_key] = int(value_from_ui)
                                except (ValueError, TypeError): config_to_write[section_key][sub_key] = self.config_template_definition[section_key][sub_key]
                            else: config_to_write[section_key][sub_key] = value_from_ui if value_from_ui is not None else ""
                        else: config_to_write[section_key][sub_key] = self.config.get(section_key, {}).get(sub_key, "")
                else:
                    if section_key in self.editor_app.config_vars:
                        value_from_ui = self.editor_app.config_vars[section_key].get()
                        config_to_write[section_key] = value_from_ui if value_from_ui is not None else ""
                    else: config_to_write[section_key] = self.config.get(section_key, section_value)

            if save_json_config(CONFIG_FILE_NAME, config_to_write, "main application config"):
                self.config = config_to_write
                if show_success_message: silent_showinfo("Success", "Main configuration saved successfully!", parent=self.editor_app.master)
                self.editor_app.load_available_files()
                self.editor_app.populate_bot_settings_tab()
                if hasattr(self.editor_app, 'lora_styles_tab_manager'): self.editor_app.lora_styles_tab_manager.populate_lora_styles_tab()
                if hasattr(self.editor_app, 'favorites_tab_manager'): self.editor_app.favorites_tab_manager.populate_all_favorites_sub_tabs()
                if hasattr(self.editor_app, 'admin_control_tab_manager'): self.editor_app.admin_control_tab_manager.populate_admin_tab()
        except Exception as e_save:
            silent_showerror("Save Error", f"Failed to save main config: {str(e_save)}", parent=self.editor_app.master)
            traceback.print_exc()


    def load_bot_settings_data(self, llm_models_data_param):
        self.llm_models_data_for_settings_template = llm_models_data_param
        current_settings_template = self.settings_template_factory()
        loaded_settings_from_file = load_json_config(SETTINGS_FILE_NAME, lambda: current_settings_template.copy(), "bot settings")
        merged_settings_result = current_settings_template.copy()
        was_settings_updated_during_load = False
        for key_template, template_default_val in current_settings_template.items():
            if key_template in loaded_settings_from_file:
                value_from_loaded_file = loaded_settings_from_file[key_template]
                try:
                    if key_template == 'default_mp_size':
                        str_val = str(value_from_loaded_file)
                        allowed_mp = ["0.25", "0.5", "1", "1.25", "1.5", "1.75", "2", "2.5", "3", "4"]
                        merged_settings_result[key_template] = str_val if str_val in allowed_mp else template_default_val
                        if merged_settings_result[key_template] != str_val: was_settings_updated_during_load = True
                    elif key_template == 'display_prompt_preference':
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
                    elif isinstance(current_settings_template_for_save.get(key_to_save), float): settings_to_write[key_to_save] = float(value_from_ui)
                    elif isinstance(current_settings_template_for_save.get(key_to_save), int): settings_to_write[key_to_save] = int(value_from_ui)
                    elif isinstance(current_settings_template_for_save.get(key_to_save), bool): settings_to_write[key_to_save] = bool(value_from_ui)
                    else: settings_to_write[key_to_save] = str(value_from_ui) if value_from_ui is not None else None
            saved_provider = settings_to_write.get('llm_provider', 'gemini')
            if 'llm_model' in self.editor_app.settings_vars:
                model_for_current_provider = self.editor_app.settings_vars['llm_model'].get()
                settings_to_write[f"llm_model_{saved_provider}"] = model_for_current_provider
            settings_to_write.pop('llm_model', None)
            if save_json_config(SETTINGS_FILE_NAME, settings_to_write, "bot settings"):
                self.settings = settings_to_write
                try: self.settings_last_mtime = os.path.getmtime(SETTINGS_FILE_NAME)
                except OSError as e_mtime: self.settings_last_mtime = 0
                if show_success_message: silent_showinfo("Success", "Bot settings saved successfully!", parent=self.editor_app.master)
        except Exception as e_save_settings:
            silent_showerror("Save Error", f"Failed to save bot settings: {str(e_save_settings)}", parent=self.editor_app.master)
            traceback.print_exc()
