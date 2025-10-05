import json
import os
import traceback

def load_main_config():
    config_path = 'config.json'
    default_structure = {
        "ADMIN": {"USERNAME": "", "ID": ""}, 
        "OUTPUTS": {}, 
        "COMFYUI_API": {"HOST": "127.0.0.1", "PORT": 8188},
        "BOT_INTERNAL_API": {"HOST": "127.0.0.1", "PORT": 8189},
        "BOT_API": {}, "LLM_ENHANCER": {"GEMINI_API_KEY": "", "GROQ_API_KEY": "", "OPENAI_API_KEY": ""}, 
        "ALLOWED_USERS": {}
    }
    try:
        if not os.path.exists(config_path):
            with open(config_path, 'w') as f: json.dump(default_structure, f, indent=2)
            return default_structure
        with open(config_path, 'r') as config_file: config_data = json.load(config_file)
        if not isinstance(config_data, dict): raise ValueError(f"{config_path} is not a valid dictionary.")
        updated = False
        for key in default_structure:
            if key not in config_data:
                config_data[key] = default_structure[key]; updated = True
        
        
        if "ADMIN" not in config_data or not isinstance(config_data["ADMIN"], dict):
            config_data["ADMIN"] = default_structure["ADMIN"]; updated = True
        else:
            if "USERNAME" not in config_data["ADMIN"]:
                config_data["ADMIN"]["USERNAME"] = ""; updated = True
            if "ID" not in config_data["ADMIN"]:
                config_data["ADMIN"]["ID"] = ""; updated = True

        if "LLM_ENHANCER" in config_data and isinstance(config_data["LLM_ENHANCER"], dict):
            if "GEMMA_API_KEY" in config_data["LLM_ENHANCER"]:
                gemma_key = config_data["LLM_ENHANCER"].pop("GEMMA_API_KEY")
                if "GEMINI_API_KEY" not in config_data["LLM_ENHANCER"] or not config_data["LLM_ENHANCER"]["GEMINI_API_KEY"]:
                    config_data["LLM_ENHANCER"]["GEMINI_API_KEY"] = gemma_key
                updated = True
        else: config_data["LLM_ENHANCER"] = default_structure["LLM_ENHANCER"]; updated = True
        if updated:
            with open(config_path, 'w') as f: json.dump(config_data, f, indent=2)
        return config_data
    except Exception as e:
        print(f"CRITICAL UNEXPECTED ERROR loading {config_path}: {e}"); traceback.print_exc()
        return default_structure

config = load_main_config()
BOT_TOKEN = config.get('BOT_API', {}).get('KEY')
ADMIN_USERNAME = config.get('ADMIN', {}).get('USERNAME', None)
ADMIN_ID = config.get('ADMIN', {}).get('ID', None)
ALLOWED_USERS = config.get('ALLOWED_USERS', {})
COMFYUI_HOST = config.get('COMFYUI_API', {}).get('HOST', '127.0.0.1')
COMFYUI_PORT = config.get('COMFYUI_API', {}).get('PORT', 8188)
BOT_INTERNAL_API_HOST = config.get('BOT_INTERNAL_API', {}).get('HOST', '127.0.0.1')
BOT_INTERNAL_API_PORT = config.get('BOT_INTERNAL_API', {}).get('PORT', 8189)

for port_var_name in ["COMFYUI_PORT", "BOT_INTERNAL_API_PORT"]:
    globals()[port_var_name] = int(globals()[port_var_name])

def print_startup_info():
    print(f"Admin User: {ADMIN_USERNAME or 'Not Set'}")
    print(f"Admin User ID: {ADMIN_ID or 'Not Set! WARNING!'}")
    print(f"ComfyUI API: http://{COMFYUI_HOST}:{COMFYUI_PORT}")
    print(f"Bot Internal API: http://{BOT_INTERNAL_API_HOST}:{BOT_INTERNAL_API_PORT}")
    print(f"Allowed Users Loaded: {len(ALLOWED_USERS)}")

def normalize_path_for_comfyui(path):
    if not path or not isinstance(path, str): return path
    if path.startswith('\\\\'):
        parts = path.split('\\', 3)
        if len(parts) > 2:
            server_share = '\\\\' + parts[2]
            rest_of_path = parts[3] if len(parts) > 3 else ""
            normalized = server_share.replace('\\', '/') + ('/' + rest_of_path.replace('\\', '/') if rest_of_path else "")
            if not rest_of_path and path.count('\\') == 3 and path.endswith('\\'): normalized = server_share.replace('\\', '/') + '/'
            elif not rest_of_path and path.count('\\') == 3 and not path.endswith('\\'): normalized = server_share.replace('\\', '/')
            return normalized
        else: return path.replace('\\', '/')
    else: return path.replace('\\', '/')

def print_output_dirs():
    output_paths = config.get('OUTPUTS', {})
    print("-" * 20); print("Output Directories (from config.json):")
    if not output_paths: print("  No output paths configured in config.json under 'OUTPUTS'.")
    else:
        for key, path_val in output_paths.items():
            if path_val and isinstance(path_val, str):
                try:
                    norm_path = os.path.normpath(path_val); abs_path = os.path.abspath(norm_path)
                    exists = os.path.exists(abs_path) and os.path.isdir(abs_path)
                    print(f"  {key}: '{path_val}' -> Exists: {exists}")
                except Exception as e_proc: print(f"ERROR processing output directory {key} - '{path_val}': {e_proc}")
            else: print(f"  {key}: Not set or invalid path in config.")
    print("-" * 20)

if not ADMIN_ID: print("CRITICAL WARNING: ADMIN User ID not set in config.json!")
