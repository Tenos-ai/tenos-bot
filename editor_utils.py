import tkinter as tk
from tkinter import filedialog
import json
import os
import traceback

from editor_constants import (
    LLM_MODELS_FILE_NAME, LLM_PROMPTS_FILE_NAME, STYLES_CONFIG_FILE_NAME,
    CONFIG_FILE_NAME, SETTINGS_FILE_NAME
)

def _dispatch_status(parent, title, message, level="info", duration=2000):
    """Route status notifications through the parent window when available."""

    target_parent = parent
    if target_parent is None and tk._default_root is not None:
        target_parent = tk._default_root

    if target_parent is not None:
        callback = getattr(target_parent, "show_status_message", None)
        if callable(callback):
            callback(f"{title}: {message}" if title else message, level=level, duration=duration)
            return True

    # Fallback to console output if no UI hook exists
    print(f"[{level.upper()}] {title}: {message}")
    return False


def silent_showinfo(title, message, parent=None, **kwargs):
    """Display an informational status message without using message boxes."""

    return _dispatch_status(parent, title, message, level="info")


def silent_showerror(title, message, parent=None, **kwargs):
    """Display an error status message without using message boxes."""

    return _dispatch_status(parent, title, message, level="error", duration=2200)


def silent_showwarning(title, message, parent=None, **kwargs):
    """Display a warning status message without using message boxes."""

    return _dispatch_status(parent, title, message, level="warning", duration=2200)


def silent_askyesno(title, message, parent=None, **kwargs):
    """Ask a yes/no question via the parent status banner when available."""

    target_parent = parent if parent is not None else tk._default_root
    if target_parent is not None:
        ask_callback = getattr(target_parent, "ask_status_yes_no", None)
        if callable(ask_callback):
            return ask_callback(title, message)
    # Fallback to a sensible default (Yes) when no UI hook is present
    print(f"[QUESTION] {title}: {message} -> defaulting to 'Yes'")
    return True


def silent_askstring(title, prompt, parent=None, **kwargs):
    """Ask for a string input via the parent status banner when available."""

    target_parent = parent if parent is not None else tk._default_root
    if target_parent is not None:
        ask_callback = getattr(target_parent, "ask_status_string", None)
        if callable(ask_callback):
            return ask_callback(title, prompt, **kwargs)
    print(f"[PROMPT] {title}: {prompt} -> no UI hook; returning None")
    return None

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

def default_llm_prompts_config_factory():

    flux_prompt = ("Your designated function is Flux Prompt Alchemist. Your input is raw user text; "
                   "your output is a single, optimized text prompt meticulously crafted for Flux.1 Dev via ComfyUI...")
    sdxl_prompt = ("You are an expert prompt enhancer for SDXL text-to-image generation. Your input is raw user text; "
                   "your output is a single, optimized text prompt meticulously crafted for SDXL via ComfyUI...")
    qwen_prompt = ("You are a visionary prompt artist for Qwen Image generation. Transform every user idea into a lush, "
                   "imaginative scene with painterly detail while respecting the user's constraints. Provide a single paragraph "
                   "of evocative prose that covers subject, setting, mood, color palette, lighting, and atmosphere without "
                   "resorting to bullet points or negative prompts.")
    wan_prompt = ("You are an expert cinematic director helping WAN create short video clips. Expand the user's seed idea into "
                  "a dynamic shot description that highlights motion cues, pacing, and visual storytelling. Mention framing, "
                  "camera movement, and mood in natural language, and tailor the motion intensity based on the requested "
                  "profile (slowmo, low, medium, high). Provide exactly one paragraph ready for storyboard execution.")
    return {
        "enhancer_system_prompt": flux_prompt,
        "enhancer_system_prompt_sdxl": sdxl_prompt,
        "enhancer_system_prompt_qwen": qwen_prompt,
        "enhancer_system_prompt_wan": wan_prompt
    }

def default_styles_config_factory():
    return {"off": {"favorite": False}}



def load_llm_models_config_util():
    config = load_json_config(LLM_MODELS_FILE_NAME, default_llm_models_config_factory, "LLM models")
    
    providers = config.get("providers", {})
    if "openai" not in providers:
        print(f"ConfigEditor: Adding default OpenAI provider to {LLM_MODELS_FILE_NAME}")
        if "providers" not in config: config["providers"] = {}
        config["providers"]["openai"] = default_llm_models_config_factory()["providers"]["openai"]
        try:
            with open(LLM_MODELS_FILE_NAME, 'w') as f_write: json.dump(config, f_write, indent=2)
        except Exception as e_write: print(f"ConfigEditor Error: Could not save updated {LLM_MODELS_FILE_NAME}: {e_write}")
    else:
        config["providers"] = providers

    for provider_key, provider_data in list(config.get("providers", {}).items()):
        if not isinstance(provider_data, dict):
            config["providers"][provider_key] = default_llm_models_config_factory()["providers"].get(
                provider_key,
                {"display_name": provider_key.capitalize(), "models": [], "favorites": []}
            )
            continue
        if "favorites" not in provider_data or not isinstance(provider_data.get("favorites"), list):
            provider_data["favorites"] = []
        else:
            provider_data["favorites"] = [
                str(model_name).strip()
                for model_name in provider_data["favorites"]
                if isinstance(model_name, str)
            ]
        if "models" in provider_data and isinstance(provider_data["models"], list):
            provider_data["models"] = [
                str(model_name).strip()
                for model_name in provider_data["models"]
                if isinstance(model_name, str)
            ]
        config["providers"][provider_key] = provider_data
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
    if not prompts.get("enhancer_system_prompt_qwen", "").strip():
        print(f"ConfigEditor Warning: 'enhancer_system_prompt_qwen' missing or empty in {LLM_PROMPTS_FILE_NAME}. Using default.")
        prompts["enhancer_system_prompt_qwen"] = defaults.get("enhancer_system_prompt_qwen", "")
        updated = True
    if not prompts.get("enhancer_system_prompt_wan", "").strip():
        print(f"ConfigEditor Warning: 'enhancer_system_prompt_wan' missing or empty in {LLM_PROMPTS_FILE_NAME}. Using default.")
        prompts["enhancer_system_prompt_wan"] = defaults.get("enhancer_system_prompt_wan", "")
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
