import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import json
import os
import traceback

from editor_constants import (
    LLM_MODELS_FILE_NAME, LLM_PROMPTS_FILE_NAME, STYLES_CONFIG_FILE_NAME,
    CONFIG_FILE_NAME, SETTINGS_FILE_NAME
)


def create_silent_dialog(master=None, **kwargs):
    """Creates a messagebox.Message object with the bell method overridden."""
    
    temp_root = None
    if master is None:
        
        if not tk._default_root:
            temp_root = tk.Tk()
            temp_root.withdraw()
        actual_master = tk._default_root if tk._default_root else temp_root
    else:
        actual_master = master

    dialog = messagebox.Message(master=actual_master, **kwargs)
    dialog.bell = lambda: None

    
    return dialog

def silent_showinfo(title, message, parent=None, **kwargs):
    """Shows an info dialog without a bell sound."""
    
    dialog = create_silent_dialog(master=parent, title=title, message=message,
                                icon=messagebox.INFO, type=messagebox.OK, **kwargs)
    return dialog.show()

def silent_showerror(title, message, parent=None, **kwargs):
    """Shows an error dialog without a bell sound."""
    dialog = create_silent_dialog(master=parent, title=title, message=message,
                                icon=messagebox.ERROR, type=messagebox.OK, **kwargs)
    return dialog.show()

def silent_showwarning(title, message, parent=None, **kwargs):
    """Shows a warning dialog without a bell sound."""
    dialog = create_silent_dialog(master=parent, title=title, message=message,
                                icon=messagebox.WARNING, type=messagebox.OK, **kwargs)
    return dialog.show()

def silent_askyesno(title, message, parent=None, **kwargs):
    """Asks a yes/no question without a bell sound if a parent is provided."""
    if parent:
        original_bell = None
        has_bell_attr = hasattr(parent, 'bell')
        if has_bell_attr:
            original_bell = parent.bell
            parent.bell = lambda: None

        result = messagebox.askyesno(title, message, parent=parent, **kwargs)

        if has_bell_attr and original_bell is not None :
            parent.bell = original_bell
        return result
    
    return messagebox.askyesno(title, message, **kwargs)

def silent_askstring(title, prompt, parent=None, **kwargs):
    """Asks for a string input without a bell sound if a parent is provided."""
    if parent:
        original_bell = None
        has_bell_attr = hasattr(parent, 'bell')
        if has_bell_attr:
            original_bell = parent.bell
            parent.bell = lambda: None
        
        
        result = simpledialog.askstring(title, prompt, parent=parent, **kwargs)

        if has_bell_attr and original_bell is not None:
            parent.bell = original_bell
        return result
    return simpledialog.askstring(title, prompt, **kwargs)

def browse_folder_dialog(parent=None, initialdir=None, title="Select Folder"):
    """Opens a folder selection dialog."""
    
    if initialdir and not os.path.isdir(initialdir):
        initialdir = os.getcwd()
    elif not initialdir:
        initialdir = os.getcwd()

    folder_path = filedialog.askdirectory(
        mustexist=True,
        parent=parent,
        initialdir=initialdir,
        title=title
    )
    return folder_path


def load_json_config(file_name, default_config_factory, description="configuration"):
    """
    Generic function to load a JSON configuration file.
    Creates a default file if it doesn't exist or is invalid.
    Args:
        file_name (str): The name of the JSON file.
        default_config_factory (callable): A function that returns the default dictionary.
        description (str): A description of the config for log messages.
    Returns:
        dict: The loaded or default configuration.
    """
    default_config = default_config_factory()
    try:
        if not os.path.exists(file_name):
            print(f"ConfigEditor: {file_name} not found. Creating default {description}.")
            with open(file_name, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config

        with open(file_name, 'r') as f:
            config = json.load(f)

        if not isinstance(config, dict):
            print(f"ConfigEditor Error: {file_name} has invalid structure (not a dict). Using default and overwriting.")
            with open(file_name, 'w') as f: json.dump(default_config, f, indent=2)
            return default_config
        return config
    except (OSError, json.JSONDecodeError) as e:
        print(f"ConfigEditor Error loading {file_name}: {e}. Creating default {description} and overwriting.")
        try:
            with open(file_name, 'w') as f: json.dump(default_config, f, indent=2)
        except Exception as e_create: print(f"ConfigEditor: Failed to create default {file_name}: {e_create}")
        return default_config
    except Exception as e:
        print(f"ConfigEditor Unexpected error loading {file_name}: {e}")
        traceback.print_exc()
        return default_config

def default_llm_models_config_factory():
    return {
        "providers": {
            "gemini": {"display_name": "Google Gemini API", "models": ["gemini-1.5-flash"]},
            "groq": {"display_name": "Groq API", "models": ["llama3-8b-8192"]},
            "openai": {"display_name": "OpenAI API", "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]}
        }
    }

def default_llm_prompts_config_factory():
    
    flux_prompt = ("Your designated function is Flux Prompt Alchemist. Your input is raw user text; "
                   "your output is a single, optimized text prompt meticulously crafted for Flux.1 Dev via ComfyUI...")
    sdxl_prompt = ("You are an expert prompt enhancer for SDXL text-to-image generation. Your input is raw user text; "
                   "your output is a single, optimized text prompt meticulously crafted for SDXL via ComfyUI...")
    return {
        "enhancer_system_prompt": flux_prompt,
        "enhancer_system_prompt_sdxl": sdxl_prompt
    }

def default_styles_config_factory():
    return {"off": {"favorite": False}}



def load_llm_models_config_util():
    config = load_json_config(LLM_MODELS_FILE_NAME, default_llm_models_config_factory, "LLM models")
    
    if "openai" not in config.get("providers", {}):
        print(f"ConfigEditor: Adding default OpenAI provider to {LLM_MODELS_FILE_NAME}")
        if "providers" not in config: config["providers"] = {}
        config["providers"]["openai"] = default_llm_models_config_factory()["providers"]["openai"]
        try:
            with open(LLM_MODELS_FILE_NAME, 'w') as f_write: json.dump(config, f_write, indent=2)
        except Exception as e_write: print(f"ConfigEditor Error: Could not save updated {LLM_MODELS_FILE_NAME}: {e_write}")
    return config

def load_llm_prompts_config_util():
    prompts = load_json_config(LLM_PROMPTS_FILE_NAME, default_llm_prompts_config_factory, "LLM prompts")
    updated = False
    defaults = default_llm_prompts_config_factory()
    if not prompts.get("enhancer_system_prompt", "").strip():
        print(f"ConfigEditor Warning: 'enhancer_system_prompt' missing or empty in {LLM_PROMPTS_FILE_NAME}. Using default.")
        prompts["enhancer_system_prompt"] = defaults["enhancer_system_prompt"]
        updated = True
    if not prompts.get("enhancer_system_prompt_sdxl", "").strip():
        print(f"ConfigEditor Warning: 'enhancer_system_prompt_sdxl' missing or empty in {LLM_PROMPTS_FILE_NAME}. Using default.")
        prompts["enhancer_system_prompt_sdxl"] = defaults["enhancer_system_prompt_sdxl"]
        updated = True
    if updated:
        save_json_config(LLM_PROMPTS_FILE_NAME, prompts, "LLM prompts")
    return prompts

def load_styles_config_editor_util():
    styles = load_json_config(STYLES_CONFIG_FILE_NAME, default_styles_config_factory, "styles")
    if 'off' not in styles or not isinstance(styles.get('off'), dict):
        styles['off'] = {"favorite": False}
        save_json_config(STYLES_CONFIG_FILE_NAME, styles, "styles after 'off' fix")
    
    keys_to_remove = [k for k, v in styles.items() if not isinstance(v, dict)]
    if keys_to_remove:
        print(f"ConfigEditor Warning: Removing invalid non-dict style entries from {STYLES_CONFIG_FILE_NAME}: {keys_to_remove}")
        for k_rem in keys_to_remove: del styles[k_rem]
        save_json_config(STYLES_CONFIG_FILE_NAME, styles, "styles after removing invalid entries")
    return styles

def save_json_config(file_name, data, description="configuration"):
    """Saves data to a JSON file."""
    try:
        with open(file_name, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"ConfigEditor: Successfully saved {description} to {file_name}.")
        return True
    except (OSError, TypeError) as e:
        print(f"ConfigEditor Error saving {description} to {file_name}: {e}")
        silent_showerror("Save Error", f"Could not save {description} to {file_name}:\n{e}", parent=None)
        return False
    except Exception as e:
        print(f"ConfigEditor Unexpected error saving {description} to {file_name}: {e}")
        traceback.print_exc()
        silent_showerror("Save Error", f"Unexpected error saving {description}:\n{e}", parent=None)
        return False
