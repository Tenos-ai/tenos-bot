import os
import json
import requests
import traceback


def _unique_preserve_order(strings):
    """Return a list of unique strings preserving their first-seen order."""
    return list(dict.fromkeys(s for s in strings if isinstance(s, str)))

def scan_models(model_directory):
    """Scan for Flux model files in the specified directory."""
    models = {
        "safetensors": [],
        "sft": [],
        "gguf": []
    }

    if not os.path.exists(model_directory):
        print(f"ModelScanner Warning: Flux Model directory does not exist: {model_directory}")
        return models

    try:
        for filename in os.listdir(model_directory):
            lower_filename = filename.lower()
            if lower_filename.endswith(".safetensors"):
                models["safetensors"].append(filename)
            elif lower_filename.endswith(".sft"):
                models["sft"].append(filename)
            elif lower_filename.endswith(".gguf"):
                models["gguf"].append(filename)
    except OSError as e:
        print(f"ModelScanner Error accessing Flux model directory {model_directory}: {e}")
    except Exception as e:
        print(f"ModelScanner Unexpected error scanning Flux models: {e}")
        traceback.print_exc()

    for key in models:
        models[key].sort(key=str.lower)

    return models

def update_models_list(config_path, output_file):
    """Update the Flux models list from the configured directory."""
    print(f"ModelScanner: Updating Flux models list ({output_file})...")
    current_favorites = []
    try:
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)

        model_directory = config.get('MODELS', {}).get('MODEL_FILES')
        if not model_directory:
            print("ModelScanner Error: MODEL_FILES path not found in config for Flux models.")
            return

        if os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    current_models_data = json.load(f)
                if isinstance(current_models_data, dict) and 'favorites' in current_models_data:
                    favs = current_models_data['favorites']
                    if isinstance(favs, list):
                        current_favorites = [str(fav) for fav in favs if isinstance(fav, str)]
                    else:
                        print(f"ModelScanner Warning: 'favorites' in {output_file} is not a list. Ignoring.")
            except (json.JSONDecodeError, OSError) as e:
                print(f"ModelScanner Warning: Error reading current Flux models file ({output_file}): {e}. Favorites might be lost.")
            except Exception as e_read:
                 print(f"ModelScanner Warning: Unexpected error reading {output_file}: {e_read}. Favorites might be lost.")


        models = scan_models(model_directory)
        models['favorites'] = _unique_preserve_order(current_favorites)

        try:
            with open(output_file, 'w') as f:
                json.dump(models, f, indent=2)
            print(f"ModelScanner: Successfully updated Flux models list in {output_file}")
        except OSError as e:
            print(f"ModelScanner Error writing Flux models file {output_file}: {e}")
        except Exception as e_write:
             print(f"ModelScanner Unexpected error writing {output_file}: {e_write}")

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ModelScanner Error reading config file {config_path}: {e}")
    except Exception as e:
        print(f"ModelScanner Unexpected error in update_models_list: {e}")
        traceback.print_exc()


def scan_checkpoints(checkpoint_directory):
    """Scan for SDXL checkpoint files in the specified directory."""
    checkpoints = {
        "checkpoints": []
    }
    
    checkpoint_extensions = [".safetensors", ".ckpt", ".pth"]

    if not os.path.exists(checkpoint_directory):
        print(f"ModelScanner Warning: SDXL Checkpoint directory does not exist: {checkpoint_directory}")
        return checkpoints

    try:
        for filename in os.listdir(checkpoint_directory):
            lower_filename = filename.lower()
            if any(lower_filename.endswith(ext) for ext in checkpoint_extensions):
                checkpoints["checkpoints"].append(filename)
    except OSError as e:
        print(f"ModelScanner Error accessing SDXL checkpoint directory {checkpoint_directory}: {e}")
    except Exception as e:
        print(f"ModelScanner Unexpected error scanning SDXL checkpoints: {e}")
        traceback.print_exc()

    checkpoints["checkpoints"].sort(key=str.lower)
    return checkpoints

def update_checkpoints_list(config_path, output_file):
    """Update the SDXL checkpoints list from the configured directory."""
    print(f"ModelScanner: Updating SDXL checkpoints list ({output_file})...")
    current_favorites = []
    try:
        with open(config_path, 'r') as config_file:
            config_data = json.load(config_file)

        checkpoint_directories = []
        checkpoint_directory = config_data.get('MODELS', {}).get('CHECKPOINTS_FOLDER')
        if checkpoint_directory:
            checkpoint_directories.append(checkpoint_directory)
        qwen_directory = config_data.get('QWEN', {}).get('MODEL_FILES')
        if qwen_directory and qwen_directory not in checkpoint_directories:
            checkpoint_directories.append(qwen_directory)

        if not checkpoint_directories:
            print("ModelScanner Error: No checkpoint directories configured for SDXL/Qwen models.")
            return

        if os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    current_checkpoints_data = json.load(f)
                if isinstance(current_checkpoints_data, dict) and 'favorites' in current_checkpoints_data:
                    favs = current_checkpoints_data['favorites']
                    if isinstance(favs, list):
                        current_favorites = [str(fav) for fav in favs if isinstance(fav, str)]
                    else:
                        print(f"ModelScanner Warning: 'favorites' in {output_file} (checkpoints) is not a list. Ignoring.")
            except (json.JSONDecodeError, OSError) as e:
                print(f"ModelScanner Warning: Error reading current SDXL checkpoints file ({output_file}): {e}. Favorites might be lost.")
            except Exception as e_read:
                 print(f"ModelScanner Warning: Unexpected error reading {output_file} (checkpoints): {e_read}. Favorites might be lost.")

        aggregated = {"checkpoints": []}
        for directory in checkpoint_directories:
            data = scan_checkpoints(directory)
            for item in data.get('checkpoints', []):
                if item not in aggregated['checkpoints']:
                    aggregated['checkpoints'].append(item)
        aggregated['checkpoints'].sort(key=str.lower)
        aggregated['favorites'] = _unique_preserve_order(current_favorites)

        try:
            with open(output_file, 'w') as f:
                json.dump(aggregated, f, indent=2)
            print(f"ModelScanner: Successfully updated SDXL checkpoints list in {output_file}")
        except OSError as e:
            print(f"ModelScanner Error writing SDXL checkpoints file {output_file}: {e}")
        except Exception as e_write:
             print(f"ModelScanner Unexpected error writing {output_file} (checkpoints): {e_write}")

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ModelScanner Error reading config file {config_path}: {e}")
    except Exception as e:
        print(f"ModelScanner Unexpected error in update_checkpoints_list: {e}")
        traceback.print_exc()


def scan_clip_files(config_path, output_file):
    """Scan for CLIP files and categorize by size."""
    print(f"ModelScanner: Updating CLIP list ({output_file})...")
    current_favorites = {'t5': [], 'clip_L': []}
    try:
        with open(config_path, 'r') as config_file:
            config_data = json.load(config_file)

        clip_directories = []
        clip_directory = config_data.get('CLIP', {}).get('CLIP_FILES')
        if clip_directory:
            clip_directories.append(clip_directory)
        qwen_clip_directory = config_data.get('QWEN', {}).get('CLIP_FILES')
        if qwen_clip_directory and qwen_clip_directory not in clip_directories:
            clip_directories.append(qwen_clip_directory)

        if not clip_directories:
            print("ModelScanner Error: CLIP directories not configured in config.json.")
            return

        clip_files = {
            "t5": [],
            "clip_L": []
        }

        for directory in clip_directories:
            if not os.path.exists(directory):
                print(f"ModelScanner Error: CLIP directory does not exist: {directory}")
                continue
            print(f"ModelScanner: CLIP directory: {directory}")
            try:
                for filename in os.listdir(directory):
                    if filename.lower().endswith(".safetensors"):
                        file_path = os.path.join(directory, filename)
                        try:
                            file_size = os.path.getsize(file_path) / (1024 * 1024 * 1024)
                            target_bucket = "t5" if file_size >= 2.0 else "clip_L"
                            if filename not in clip_files[target_bucket]:
                                clip_files[target_bucket].append(filename)
                        except OSError as e:
                            print(f"ModelScanner Error accessing file {file_path}: {e}")
                        except Exception as e_size:
                            print(f"ModelScanner Unexpected error getting size for {file_path}: {e_size}")
            except OSError as e:
                print(f"ModelScanner Error listing CLIP directory: {e}")
            except Exception as e_list:
                print(f"ModelScanner Unexpected error listing CLIP directory: {e_list}")

        for key in clip_files:
            clip_files[key].sort(key=str.lower)

        if os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    current_clips_data = json.load(f)
                if isinstance(current_clips_data, dict) and 'favorites' in current_clips_data:
                    fav_data = current_clips_data['favorites']
                    if isinstance(fav_data, dict):
                        t5_favs = fav_data.get('t5', [])
                        l_favs = fav_data.get('clip_L', [])
                        current_favorites['t5'] = [str(f) for f in t5_favs if isinstance(f, str)] if isinstance(t5_favs, list) else []
                        current_favorites['clip_L'] = [str(f) for f in l_favs if isinstance(f, str)] if isinstance(l_favs, list) else []
                    else:
                         print(f"ModelScanner Warning: 'favorites' in {output_file} is not a dictionary. Ignoring old favorites.")
            except (json.JSONDecodeError, OSError) as e:
                print(f"ModelScanner Warning: Error reading current CLIP file ({output_file}): {e}. Favorites might be lost.")
            except Exception as e_read:
                 print(f"ModelScanner Warning: Unexpected error reading {output_file}: {e_read}. Favorites might be lost.")

        clip_files['favorites'] = {
            't5': _unique_preserve_order(current_favorites.get('t5', [])),
            'clip_L': _unique_preserve_order(current_favorites.get('clip_L', [])),
        }

        try:
            with open(output_file, 'w') as f:
                json.dump(clip_files, f, indent=2)
            print(f"ModelScanner: Successfully updated CLIP list in {output_file}")
        except OSError as e:
            print(f"ModelScanner Error writing CLIP file {output_file}: {e}")
        except Exception as e_write:
             print(f"ModelScanner Unexpected error writing {output_file}: {e_write}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ModelScanner Error reading config file {config_path}: {e}")
    except Exception as e:
        print(f"ModelScanner Unexpected error in scan_clip_files: {e}")
        traceback.print_exc()

def get_models_list(output_file):
    """Get the current Flux models list from file."""
    if not os.path.exists(output_file):
        print(f"ModelScanner Warning: Flux models list file {output_file} not found.")
        return None
    try:
        with open(output_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"ModelScanner Error reading Flux models list: {e}")
        return None
    except Exception as e_read:
         print(f"ModelScanner Unexpected error reading Flux models list {output_file}: {e_read}")
         return None

def get_checkpoints_list(output_file):
    """Get the current SDXL checkpoints list from file."""
    if not os.path.exists(output_file):
        print(f"ModelScanner Warning: SDXL checkpoints list file {output_file} not found.")
        return None
    try:
        with open(output_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"ModelScanner Error reading SDXL checkpoints list {output_file}: {e}")
        return None
    except Exception as e_read:
        print(f"ModelScanner Unexpected error reading SDXL checkpoints list {output_file}: {e_read}")
        return None


def get_clip_list(output_file):
    """Get the current CLIP list from file."""
    if not os.path.exists(output_file):
        print(f"ModelScanner Warning: CLIP list file {output_file} not found.")
        return None
    try:
        with open(output_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"ModelScanner Error reading CLIP list: {e}")
        return None
    except Exception as e_read:
         print(f"ModelScanner Unexpected error reading CLIP list {output_file}: {e_read}")
         return None


def verify_models_exist():
    print("ModelScanner: verify_models_exist() called - validation should occur within settings_manager or bot startup.")
    return True


if __name__ == "__main__":
    print("Running Model Scanner directly...")
    update_models_list('config.json', 'modelslist.json')
    update_checkpoints_list('config.json', 'checkpointslist.json')
    scan_clip_files('config.json', 'cliplist.json')
    print("Model Scanner finished.")
