import json
import uuid
import os
import re
import traceback
from typing import List, Dict, Any, Tuple

from queue_manager import queue_manager
from settings_manager import load_settings
from kontext_templates import get_kontext_workflow
from modelnodes import get_model_node

try:
    if not os.path.exists('config.json'):
        raise FileNotFoundError("config.json not found in kontext_editing.py.")
    with open('config.json', 'r') as config_file:
        config_data_kontext = json.load(config_file)
    if not isinstance(config_data_kontext, dict):
        raise ValueError("config.json is not a valid dictionary in kontext_editing.py.")
    
    KONTEXT_EDITS_DIR = config_data_kontext.get('OUTPUTS', {}).get('KONTEXT_EDITS', 
                        config_data_kontext.get('OUTPUTS', {}).get('GENERATIONS', 
                        os.path.join('output', 'TENOSAI-BOT', 'GENERATIONS')))
    
    if not isinstance(KONTEXT_EDITS_DIR, str) or not KONTEXT_EDITS_DIR:
        print("Warning: Invalid 'KONTEXT_EDITS' or 'GENERATIONS' path in config. Using default.")
        KONTEXT_EDITS_DIR = os.path.join('output', 'TENOSAI-BOT', 'GENERATIONS')
    if not os.path.isabs(KONTEXT_EDITS_DIR):
        KONTEXT_EDITS_DIR = os.path.abspath(KONTEXT_EDITS_DIR)
except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError) as e:
    print(f"Error loading config.json in kontext_editing.py: {e}")
    KONTEXT_EDITS_DIR = os.path.abspath(os.path.join('output', 'TENOSAI-BOT', 'GENERATIONS'))
except Exception as e:
    print(f"Unexpected error loading config.json in kontext_editing.py: {e}")
    traceback.print_exc()
    KONTEXT_EDITS_DIR = os.path.abspath(os.path.join('output', 'TENOSAI-BOT', 'GENERATIONS'))


def normalize_path_for_comfyui(path: str) -> str:
    if not path or not isinstance(path, str): return path
    return path.replace('\\', '/')

def modify_kontext_prompt(
    image_urls: List[str],
    instruction: str,
    user_settings: Dict[str, Any],
    base_seed: int,
    aspect_ratio: str,
    steps_override: int,
    guidance_override: float,
    source_job_id: str = "unknown"
) -> Tuple[str | None, Dict | None, str | None, Dict | None]:
    
    kontext_job_id = str(uuid.uuid4())[:8]
    num_images = len(image_urls)

    if not (1 <= num_images <= 4):
        return None, None, "Invalid number of images. Kontext edits require 1 to 4 images.", None

    try:
        workflow = get_kontext_workflow(num_images)

        kontext_model_name = user_settings.get('selected_kontext_model')
        vae_model_name = user_settings.get('selected_vae', 'ae.safetensors')

        if not kontext_model_name:
            return None, None, "Kontext edit model is not configured in bot settings.", None
        
        if kontext_model_name.lower().endswith(".safetensors"):
             workflow["kontext_model_loader"]["class_type"] = "UNETLoader"
             workflow["kontext_model_loader"]["inputs"]["weight_dtype"] = "default"
        else:
             workflow["kontext_model_loader"]["class_type"] = "UnetLoaderGGUF"
             if "weight_dtype" in workflow["kontext_model_loader"]["inputs"]:
                 del workflow["kontext_model_loader"]["inputs"]["weight_dtype"]

        workflow["kontext_model_loader"]["inputs"]["unet_name"] = kontext_model_name
        workflow["vae_loader"]["inputs"]["vae_name"] = vae_model_name

        for i in range(num_images):
            workflow[f"load_image_{i+1}"]["inputs"]["url_or_path"] = image_urls[i]
        

        workflow["instruction_encoder"]["inputs"]["text"] = instruction
        workflow["ksampler"]["inputs"]["seed"] = base_seed
        workflow["latent_optimizer"]["inputs"]["aspect_ratio"] = aspect_ratio
        
        workflow["ksampler"]["inputs"]["steps"] = steps_override
        workflow["flux_guidance"]["inputs"]["guidance"] = guidance_override
        
        os.makedirs(KONTEXT_EDITS_DIR, exist_ok=True)
        filename_suffix = f"_from_{source_job_id}" if source_job_id != "unknown" else ""
        filename_prefix = normalize_path_for_comfyui(
            os.path.join(KONTEXT_EDITS_DIR, f"EDIT_{kontext_job_id}{filename_suffix}")
        )
        workflow["save_image"]["inputs"]["filename_prefix"] = filename_prefix

        status_message = f"Kontext edit job {kontext_job_id} prepared."
        job_details = {
            "job_id": kontext_job_id, "type": "kontext_edit", "prompt": instruction,
            "seed": base_seed, "steps": steps_override, "guidance": guidance_override,
            "aspect_ratio_str": aspect_ratio, "image_urls": image_urls,
            "kontext_model_used": kontext_model_name, "source_job_id": source_job_id,
            "batch_size": 1, "model_type_for_enhancer": "kontext" 
        }

        return kontext_job_id, workflow, status_message, job_details

    except Exception as e:
        print(f"CRITICAL ERROR in modify_kontext_prompt: {e}")
        traceback.print_exc()
        return None, None, "An internal error occurred while building the Kontext workflow.", None
